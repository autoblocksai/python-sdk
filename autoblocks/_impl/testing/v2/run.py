import asyncio
import contextvars
import functools
import inspect
import json
import logging
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Sequence
from typing import Union
from typing import overload

from opentelemetry import trace
from opentelemetry.baggage import set_baggage
from opentelemetry.context import attach
from opentelemetry.context import detach
from opentelemetry.context import get_current

from autoblocks._impl import global_state
from autoblocks._impl.context_vars import EvaluatorRunContext
from autoblocks._impl.context_vars import TestCaseRunContext
from autoblocks._impl.context_vars import TestRunContext
from autoblocks._impl.context_vars import evaluator_run_context_var
from autoblocks._impl.context_vars import grid_search_context_var
from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.context_vars import test_run_context_var
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import CreateHumanReviewJob
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import EvaluationWithId
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.util import GridSearchParams
from autoblocks._impl.testing.util import GridSearchParamsCombo
from autoblocks._impl.testing.util import yield_grid_search_param_combos
from autoblocks._impl.testing.util import yield_test_case_contexts_from_test_cases
from autoblocks._impl.tracer.util import SpanAttribute
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled
from autoblocks._impl.util import cuid_generator
from autoblocks._impl.util import serialize

log = logging.getLogger(__name__)

test_case_semaphore_registry: dict[str, asyncio.Semaphore] = {}  # test_id -> semaphore
evaluator_semaphore_registry: dict[str, dict[str, asyncio.Semaphore]] = {}  # test_id -> evaluator_id -> semaphore

DEFAULT_MAX_TEST_CASE_CONCURRENCY = 10


def tests_and_hashes_overrides_map() -> Optional[dict[str, list[str]]]:
    """
    AUTOBLOCKS_OVERRIDES_TESTS_AND_HASHES is a JSON string that maps test suite IDs to a list of test case hashes.
    This is set when a user triggers a test run from the UI so that we only run the given test suite, and,
    if applicable, only the given test cases.
    """
    raw = AutoblocksEnvVar.OVERRIDES_TESTS_AND_HASHES.get()
    if not raw:
        return None
    return json.loads(raw)  # type: ignore


def filters_test_suites_list() -> list[str]:
    """
    AUTOBLOCKS_FILTERS_TEST_SUITES is a list of test suite IDs that should be run.
    This is set from the CLI, and we fuzzy match the test suite IDs to determine which test suites to run.
    """
    raw = AutoblocksEnvVar.FILTERS_TEST_SUITES.get()
    if not raw:
        return []
    return json.loads(raw)  # type: ignore


async def run_evaluator_unsafe(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: Any,
    hook_results: Any,
    evaluator: BaseTestEvaluator,
) -> Optional[Evaluation]:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    evaluation: Optional[Evaluation] | Awaitable[Optional[Evaluation]] = None
    async with evaluator_semaphore_registry[test_id][evaluator.id]:
        if hook_results is not None:
            kwargs = dict(hook_results=hook_results)
        else:
            kwargs = dict()

        if inspect.iscoroutinefunction(evaluator.evaluate_test_case):
            evaluation = await evaluator.evaluate_test_case(test_case_ctx.test_case, output, **kwargs)
        else:
            ctx = contextvars.copy_context()
            evaluation = await global_state.event_loop().run_in_executor(
                None,
                ctx.run,
                functools.partial(
                    evaluator.evaluate_test_case,
                    test_case_ctx.test_case,
                    output,
                    **kwargs,
                ),
            )
    if isinstance(evaluation, Awaitable):
        evaluation = await evaluation
    return evaluation


async def run_evaluator(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: Any,
    hook_results: Any,
    evaluator: BaseTestEvaluator,
) -> Optional[EvaluationWithId]:
    reset_token = evaluator_run_context_var.set(
        EvaluatorRunContext(),
    )
    evaluation: Evaluation | None = None
    try:
        evaluation = await run_evaluator_unsafe(
            test_id=test_id,
            test_case_ctx=test_case_ctx,
            output=output,
            hook_results=hook_results,
            evaluator=evaluator,
        )
    except Exception as err:
        log.error(f"Error running evaluator '{evaluator.id}' for test case '{test_case_ctx.hash()}'", exc_info=err)
    finally:
        evaluator_run_context_var.reset(reset_token)

    if evaluation is None:
        return None

    return EvaluationWithId(
        id=evaluator.id,
        score=evaluation.score,
        threshold=evaluation.threshold,
        metadata=evaluation.metadata,
        assertions=evaluation.assertions,
    )


async def run_test_case_unsafe(
    test_id: str,
    app_slug: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    fn: Union[Callable[[TestCaseType], Any], Callable[[TestCaseType], Awaitable[Any]]],
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]],
    evaluators: Sequence[BaseTestEvaluator],
) -> None:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    execution_id = cuid_generator()
    # Get current context and set baggage
    otel_ctx = get_current()
    otel_ctx = set_baggage(SpanAttribute.EXECUTION_ID, execution_id, context=otel_ctx)
    otel_ctx = set_baggage(SpanAttribute.ENVIRONMENT, "test", context=otel_ctx)
    otel_ctx = set_baggage(SpanAttribute.APP_SLUG, app_slug, context=otel_ctx)
    tracer = trace.get_tracer("AUTOBLOCKS_TRACER")
    token = attach(otel_ctx)
    async with test_case_semaphore_registry[test_id]:
        with tracer.start_as_current_span(app_slug, context=otel_ctx) as span:
            # Set span attributes before function execution
            span.set_attribute(SpanAttribute.IS_ROOT, True)
            span.set_attribute(SpanAttribute.EXECUTION_ID, execution_id)
            span.set_attribute(SpanAttribute.ENVIRONMENT, "test")
            span.set_attribute(SpanAttribute.APP_SLUG, app_slug)
            span.set_attribute(SpanAttribute.INPUT, serialize(test_case_ctx.test_case))
            if inspect.iscoroutinefunction(fn):
                output = await fn(test_case_ctx.test_case)
            else:
                ctx = contextvars.copy_context()
                output = await global_state.event_loop().run_in_executor(
                    None,
                    ctx.run,
                    fn,
                    test_case_ctx.test_case,
                )
            span.set_attribute(SpanAttribute.OUTPUT, serialize(output))

            # Run the before-evaluators hook if provided.
            # Note we run this within the test case semaphore so that
            # max_test_case_concurrency applies to both fn + before_evaluators_hook.
            hook_results = None
            if before_evaluators_hook:
                if inspect.iscoroutinefunction(before_evaluators_hook):
                    hook_results = await before_evaluators_hook(
                        test_case_ctx.test_case,
                        output,
                    )
                else:
                    ctx = contextvars.copy_context()
                    hook_results = await global_state.event_loop().run_in_executor(
                        None,
                        ctx.run,
                        before_evaluators_hook,
                        test_case_ctx.test_case,
                        output,
                    )

            evaluator_results_futures = await all_settled(
                [
                    run_evaluator(
                        test_id=test_id,
                        test_case_ctx=test_case_ctx,
                        output=output,
                        hook_results=hook_results,
                        evaluator=evaluator,
                    )
                    for evaluator in evaluators
                ],
            )
            evaluator_results: list[EvaluationWithId] = []
            for result in evaluator_results_futures:
                if isinstance(result, Exception):
                    log.error(f"Error running evaluator for test case '{test_case_ctx.hash()}'", exc_info=result)
                elif isinstance(result, EvaluationWithId):
                    evaluator_results.append(result)
            span.set_attribute(SpanAttribute.EVALUATORS, serialize(evaluator_results))

    detach(token)


async def run_test_case(
    test_id: str,
    run_id: str,
    app_slug: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator],
    fn: Union[Callable[[TestCaseType], Any], Callable[[TestCaseType], Awaitable[Any]]],
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]],
) -> None:
    reset_token = test_case_run_context_var.set(
        TestCaseRunContext(
            run_id=run_id,
            test_id=test_id,
            test_case_hash=test_case_ctx.hash(),
        ),
    )
    try:
        await run_test_case_unsafe(
            test_id=test_id,
            app_slug=app_slug,
            test_case_ctx=test_case_ctx,
            fn=fn,
            before_evaluators_hook=before_evaluators_hook,
            evaluators=evaluators,
        )
    except Exception as err:
        log.error(f"Error running test case '{test_case_ctx.hash()}'", exc_info=err)
        return
    finally:
        test_case_run_context_var.reset(reset_token)


def validate_test_suite_inputs(
    test_id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator],
    grid_search_params: Optional[GridSearchParams],
) -> None:
    assert test_cases, f"[{test_id}] No test cases provided."
    test_case_hashes = set()
    for test_case in test_cases:
        assert isinstance(
            test_case,
            BaseTestCase,
        ), f"[{test_id}] Test case {test_case} does not implement {BaseTestCase.__name__}."
        test_case_hash = test_case.hash()
        assert test_case_hash not in test_case_hashes, (
            f"[{test_id}] Duplicate test case hash: '{test_case_hash}'. "
            "See https://docs.autoblocks.ai/testing/sdk-reference#test-case-hashing"
        )
        test_case_hashes.add(test_case_hash)

    evaluator_ids = set()
    for evaluator in evaluators:
        assert isinstance(
            evaluator,
            BaseTestEvaluator,
        ), f"[{test_id}] Evaluator {evaluator} does not implement {BaseTestEvaluator.__name__}."
        evaluator_id = evaluator.id
        assert (
            evaluator_id not in evaluator_ids
        ), f"[{test_id}] Duplicate evaluator id: '{evaluator_id}'. Each evaluator id must be unique."
        evaluator_ids.add(evaluator_id)

    if grid_search_params is not None:
        assert isinstance(
            grid_search_params,
            dict,
        ), f"[{test_id}] grid_search_params must be a dict."
        for key, values in grid_search_params.items():
            assert isinstance(
                key,
                str,
            ), f"[{test_id}] grid_search_params keys must be strings."
            assert isinstance(
                values,
                Sequence,
            ), f"[{test_id}] grid_search_params values must be sequences."
            assert values, f"[{test_id}] grid_search_params values must not be empty."


def filter_test_cases_for_alignment_mode(
    test_id: str,
    test_cases: Sequence[TestCaseType],
) -> Sequence[TestCaseType]:
    """
    A test suite is in "alignment mode" if the user has started an "alignment session" via the CLI:

    $ npx autoblocks testing align --test-suite-id <test-suite-id> -- <cmd>

    This starts an interactive CLI where single test cases from the suite are run through `fn`,
    and the user then provides feedback on the output. This function checks for the environment
    variables that the CLI sets during an alignment session and filters the test cases accordingly.
    """
    # Double check this is the correct test suite
    assert AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.get() == test_id

    align_test_case_hash = AutoblocksEnvVar.ALIGN_TEST_CASE_HASH.get()
    if not align_test_case_hash:
        # The first time a test suite is run in alignment mode, the CLI will not provide a test case hash,
        # so we run the first one. On subsequent runs, the CLI will provide a test case hash since it
        # will have then received the /info request with the list of test case hashes.
        return [test_cases[0]]

    # Only run the selected test case
    return [test_case for test_case in test_cases if test_case.hash() == align_test_case_hash]


async def run_test_suite_for_grid_combo(
    test_id: str,
    app_slug: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator],
    fn: Union[Callable[[TestCaseType], Any], Callable[[TestCaseType], Awaitable[Any]]],
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]],
    grid_search_params_combo: Optional[GridSearchParamsCombo],
    human_review_job: Optional[CreateHumanReviewJob],
) -> None:
    run_id = cuid_generator()
    test_run_reset_token = test_run_context_var.set(
        TestRunContext(run_id=run_id, run_message=AutoblocksEnvVar.TEST_RUN_MESSAGE.get(), test_id=test_id)
    )
    grid_search_reset_token = (
        grid_search_context_var.set(grid_search_params_combo) if grid_search_params_combo else None
    )

    try:
        await all_settled(
            [
                run_test_case(
                    test_id=test_id,
                    run_id=run_id,
                    app_slug=app_slug,
                    test_case_ctx=test_case_ctx,
                    evaluators=evaluators,
                    fn=fn,
                    before_evaluators_hook=before_evaluators_hook,
                )
                for test_case_ctx in yield_test_case_contexts_from_test_cases(test_cases)
            ],
        )
    except Exception as err:
        log.error(f"Error running test suite '{test_id}'", exc_info=err)
    finally:
        if grid_search_reset_token:
            grid_search_context_var.reset(grid_search_reset_token)
        if test_run_reset_token:
            test_run_context_var.reset(test_run_reset_token)

    # if human_review_job is not None:
    #     try:
    #         assignee_email_addresses = human_review_job.get_assignee_email_addresses()
    #         await all_settled(
    #             [
    #                 send_create_human_review_job(
    #                     run_id=run_id,
    #                     assignee_email_address=assignee_email_address,
    #                     name=human_review_job.name,
    #                 )
    #                 for assignee_email_address in assignee_email_addresses
    #             ]
    #         )
    #     except Exception as err:
    #         log.warn(f"Failed to create human review job for test run '{run_id}'", exc_info=err)

    # await all_settled(
    #     [
    #         send_slack_notification(run_id=run_id),
    #         send_github_comment(),
    #     ]
    # )


async def async_run_test_suite(
    test_id: str,
    app_slug: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator],
    fn: Union[Callable[[TestCaseType], Any], Callable[[TestCaseType], Awaitable[Any]]],
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]],
    max_test_case_concurrency: int,
    grid_search_params: Optional[GridSearchParams],
    human_review_job: Optional[CreateHumanReviewJob],
) -> None:

    # This will be set if the user passed filters to the CLI
    # we do a substring match to allow for fuzzy matching
    # For example a filter of "ell" would match a test suite of "hello"
    filters_test_suites = filters_test_suites_list()
    if len(filters_test_suites) > 0 and not any(filter_id in test_id for filter_id in filters_test_suites):
        log.info(f"Skipping test suite '{test_id}' because it is not in the list of test suites to run.")
        return

    # This will be set if a user has triggered a run from the UI for a particular test suite.
    # If it is not this test suite, then we skip it.
    tests_and_hashes = tests_and_hashes_overrides_map()
    if tests_and_hashes:
        if test_id not in tests_and_hashes:
            log.info(f"Skipping test suite '{test_id}' because it is not in the list of test suites to run.")
            return

        # If the value for this test suite is non-empty, then it is a list of test case
        # hashes to run. We filter the test cases to only run those.
        hashes_to_run = set(tests_and_hashes[test_id] or [])
        if hashes_to_run:
            test_cases = [tc for tc in test_cases if tc.hash() in hashes_to_run]

    try:
        validate_test_suite_inputs(
            test_id=test_id,
            test_cases=test_cases,
            evaluators=evaluators,
            grid_search_params=grid_search_params,
        )
    except Exception as err:
        log.error(f"Error validating test suite inputs for '{test_id}'", exc_info=err)
        return

    # Initialize the semaphore registries
    test_case_semaphore_registry[test_id] = asyncio.Semaphore(max_test_case_concurrency)
    evaluator_semaphore_registry[test_id] = {
        evaluator.id: asyncio.Semaphore(evaluator.max_concurrency) for evaluator in evaluators
    }

    if grid_search_params is None:
        try:
            log.debug(f"No grid search params provided for test suite '{test_id}'")
            await run_test_suite_for_grid_combo(
                test_id=test_id,
                app_slug=app_slug,
                test_cases=test_cases,
                evaluators=evaluators,
                fn=fn,
                before_evaluators_hook=before_evaluators_hook,
                grid_search_params_combo=None,
                human_review_job=human_review_job,
            )
        except Exception as err:
            log.error(f"Error running test suite '{test_id}'", exc_info=err)
        return

    try:
        await all_settled(
            [
                run_test_suite_for_grid_combo(
                    test_id=test_id,
                    app_slug=app_slug,
                    test_cases=test_cases,
                    evaluators=evaluators,
                    fn=fn,
                    before_evaluators_hook=before_evaluators_hook,
                    grid_search_params_combo=grid_params_combo,
                    human_review_job=human_review_job,
                )
                for grid_params_combo in yield_grid_search_param_combos(grid_search_params)
            ],
        )
    except Exception as err:
        log.error(f"Error running test suite '{test_id}'", exc_info=err)


# Sync fn
@overload
def run_test_suite(
    id: str,
    app_slug: str,
    test_cases: Sequence[TestCaseType],
    fn: Callable[[TestCaseType], Any],
    evaluators: Optional[Sequence[BaseTestEvaluator]] = None,
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]] = None,
    grid_search_params: Optional[GridSearchParams] = None,
    human_review_job: Optional[CreateHumanReviewJob] = None,
) -> None: ...


# Async fn
@overload
def run_test_suite(
    id: str,
    app_slug: str,
    test_cases: Sequence[TestCaseType],
    fn: Callable[[TestCaseType], Awaitable[Any]],
    evaluators: Optional[Sequence[BaseTestEvaluator]] = None,
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]] = None,
    grid_search_params: Optional[GridSearchParams] = None,
    human_review_job: Optional[CreateHumanReviewJob] = None,
) -> None: ...


def run_test_suite(
    id: str,
    app_slug: str,
    test_cases: Sequence[TestCaseType],
    fn: Union[Callable[[TestCaseType], Any], Callable[[TestCaseType], Awaitable[Any]]],
    evaluators: Optional[Sequence[BaseTestEvaluator]] = None,
    # How many test cases to run concurrently
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
    before_evaluators_hook: Optional[Callable[[TestCaseType, Any], Any]] = None,
    grid_search_params: Optional[GridSearchParams] = None,
    human_review_job: Optional[CreateHumanReviewJob] = None,
) -> None:
    if not global_state.is_auto_tracer_initialized():
        log.error(
            "Autoblocks auto tracer is not initialized and is required for test suite runs."
            "Please call init_auto_tracer() first."
        )
        return
    log.info(f"Running test suite '{id}'")
    global_state.init()

    asyncio.run_coroutine_threadsafe(
        async_run_test_suite(
            test_id=id,
            app_slug=app_slug,
            test_cases=test_cases,
            evaluators=evaluators or [],
            fn=fn,
            before_evaluators_hook=before_evaluators_hook,
            max_test_case_concurrency=max_test_case_concurrency,
            grid_search_params=grid_search_params,
            human_review_job=human_review_job,
        ),
        global_state.event_loop(),
    ).result()

    log.info(f"Finished running test suite '{id}'")

    # Force flush the tracer provider to send all results to Autoblocks
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
