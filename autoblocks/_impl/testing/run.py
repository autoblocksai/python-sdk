import asyncio
import contextvars
import dataclasses
import inspect
import logging
import os
import traceback
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Sequence
from typing import Union
from typing import overload

from httpx import HTTPStatusError
from httpx import Response

from autoblocks._impl import global_state
from autoblocks._impl.context_vars import TestCaseRunContext
from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.util import serialize
from autoblocks._impl.testing.util import serialize_test_case
from autoblocks._impl.testing.util import yield_test_case_contexts_from_test_cases
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled

log = logging.getLogger(__name__)

test_case_semaphore_registry: dict[str, asyncio.Semaphore] = {}  # test_id -> semaphore
evaluator_semaphore_registry: dict[str, dict[str, asyncio.Semaphore]] = {}  # test_id -> evaluator_id -> semaphore

DEFAULT_MAX_TEST_CASE_CONCURRENCY = 10


def cli() -> str:
    """
    Returns the CLI server address, which is required to send results and errors to the CLI.
    """
    cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
    if not cli_server_address:
        raise RuntimeError(
            "Autoblocks tests must be run within the context of the testing CLI.\n"
            "Make sure you are running your test command with:\n"
            "$ npx autoblocks testing exec -- <your test command>"
        )
    return cli_server_address


async def post_to_cli(
    path: str,
    json: dict[str, Any],
) -> Response:
    return await global_state.http_client().post(
        f"{cli()}{path}",
        json=json,
        timeout=15,  # seconds
    )


async def send_error(
    test_id: str,
    test_case_hash: Optional[str],
    evaluator_id: Optional[str],
    error: Exception,
) -> None:
    await post_to_cli(
        "/errors",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case_hash,
            evaluatorExternalId=evaluator_id,
            error=dict(
                name=type(error).__name__,
                message=str(error),
                stacktrace=traceback.format_exc(),
            ),
        ),
    )


async def run_evaluator_unsafe(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: OutputType,
    evaluator: BaseTestEvaluator[TestCaseType, OutputType],
) -> None:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    async with evaluator_semaphore_registry[test_id][evaluator.id]:
        if inspect.iscoroutinefunction(evaluator.evaluate_test_case):
            evaluation = await evaluator.evaluate_test_case(test_case_ctx.test_case, output)
        else:
            ctx = contextvars.copy_context()
            evaluation = await global_state.event_loop().run_in_executor(
                None,
                ctx.run,
                evaluator.evaluate_test_case,
                test_case_ctx.test_case,
                output,
            )

    if evaluation is None:
        return

    await post_to_cli(
        "/evals",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case_ctx.hash(),
            evaluatorExternalId=evaluator.id,
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
            metadata=evaluation.metadata,
        ),
    )


async def run_evaluator(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: OutputType,
    evaluator: BaseTestEvaluator[TestCaseType, OutputType],
) -> None:
    try:
        await run_evaluator_unsafe(
            test_id=test_id,
            test_case_ctx=test_case_ctx,
            output=output,
            evaluator=evaluator,
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case_ctx.hash(),
            evaluator_id=evaluator.id,
            error=err,
        )


async def run_test_case_unsafe(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    fn: Union[Callable[[TestCaseType], OutputType], Callable[[TestCaseType], Awaitable[OutputType]]],
) -> Any:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    async with test_case_semaphore_registry[test_id]:
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

    await post_to_cli(
        "/results",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case_ctx.hash(),
            testCaseBody=serialize_test_case(test_case_ctx.test_case),
            testCaseOutput=serialize(output),
        ),
    )
    return output


async def run_test_case(
    test_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
    fn: Union[Callable[[TestCaseType], OutputType], Callable[[TestCaseType], Awaitable[OutputType]]],
) -> None:
    token = test_case_run_context_var.set(TestCaseRunContext(test_id=test_id, test_case_hash=test_case_ctx.hash()))
    try:
        output = await run_test_case_unsafe(
            test_id=test_id,
            test_case_ctx=test_case_ctx,
            fn=fn,
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case_ctx.hash(),
            evaluator_id=None,
            error=err,
        )
        return
    finally:
        test_case_run_context_var.reset(token)

    try:
        await all_settled(
            [
                run_evaluator(
                    test_id=test_id,
                    test_case_ctx=test_case_ctx,
                    output=output,
                    evaluator=evaluator,
                )
                for evaluator in evaluators
            ],
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case_ctx.hash(),
            evaluator_id=None,
            error=err,
        )


def validate_test_suite_inputs(
    test_id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
) -> None:
    assert test_cases, f"[{test_id}] No test cases provided."
    for test_case in test_cases:
        assert isinstance(
            test_case,
            BaseTestCase,
        ), f"[{test_id}] Test case {test_case} does not implement {BaseTestCase.__name__}."
    for evaluator in evaluators:
        assert isinstance(
            evaluator,
            BaseTestEvaluator,
        ), f"[{test_id}] Evaluator {evaluator} does not implement {BaseTestEvaluator.__name__}."


async def send_info_for_alignment_mode(
    test_id: str,
    test_cases: Sequence[TestCaseType],
    caller_filepath: Optional[str],
) -> None:
    """
    Notifies the CLI with metadata about this test suite when running in "alignment mode",
    i.e. npx autoblocks testing align -- <cmd>
    """
    # Double check this is the correct test suite
    assert AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.get() == test_id

    # Tells the CLI what it needs to know about this test suite
    await post_to_cli(
        "/info",
        json=dict(
            language="python",
            runTestSuiteCalledFromDirectory=os.path.dirname(caller_filepath) if caller_filepath else None,
            testCaseHashes=[test_case.hash() for test_case in test_cases],
        ),
    )


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


async def async_run_test_suite(
    test_id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
    fn: Union[Callable[[TestCaseType], OutputType], Callable[[TestCaseType], Awaitable[OutputType]]],
    max_test_case_concurrency: int,
    caller_filepath: Optional[str],
) -> None:
    # Handle alignment mode
    align_test_id = AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.get()
    if align_test_id:
        if align_test_id != test_id:
            # Not the test suite in alignment mode
            return

        await send_info_for_alignment_mode(
            test_id=test_id,
            test_cases=test_cases,
            caller_filepath=caller_filepath,
        )
        test_cases = filter_test_cases_for_alignment_mode(
            test_id=test_id,
            test_cases=test_cases,
        )

    try:
        validate_test_suite_inputs(
            test_id=test_id,
            test_cases=test_cases,
            evaluators=evaluators,
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=None,
            evaluator_id=None,
            error=err,
        )
        return

    # Initialize the semaphore registries
    test_case_semaphore_registry[test_id] = asyncio.Semaphore(max_test_case_concurrency)
    evaluator_semaphore_registry[test_id] = {
        evaluator.id: asyncio.Semaphore(evaluator.max_concurrency) for evaluator in evaluators
    }

    start_resp = await post_to_cli(
        "/start",
        json=dict(testExternalId=test_id),
    )
    try:
        start_resp.raise_for_status()
    except HTTPStatusError:
        # Don't allow the run to continue if /start failed, since all subsequent
        # requests will fail if the CLI was not able to start the run.
        # Also note we don't need to send_error here, since the CLI will
        # have reported the HTTP error itself.
        return

    try:
        await all_settled(
            [
                run_test_case(
                    test_id=test_id,
                    test_case_ctx=test_case_ctx,
                    evaluators=evaluators,
                    fn=fn,
                )
                for test_case_ctx in yield_test_case_contexts_from_test_cases(test_cases)
            ],
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=None,
            evaluator_id=None,
            error=err,
        )

    await post_to_cli(
        "/end",
        json=dict(testExternalId=test_id),
    )


# Sync fn
@overload
def run_test_suite(
    id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
    fn: Callable[[TestCaseType], OutputType],
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
) -> None: ...


# Async fn
@overload
def run_test_suite(
    id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
    fn: Callable[[TestCaseType], Awaitable[OutputType]],
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
) -> None: ...


def run_test_suite(
    id: str,
    test_cases: Sequence[TestCaseType],
    evaluators: Sequence[BaseTestEvaluator[TestCaseType, OutputType]],
    fn: Union[Callable[[TestCaseType], OutputType], Callable[[TestCaseType], Awaitable[OutputType]]],
    # How many test cases to run concurrently
    max_test_case_concurrency: int = DEFAULT_MAX_TEST_CASE_CONCURRENCY,
) -> None:
    global_state.init()

    # Get the caller's filepath. Used in alignment mode to know where the test suite is located.
    try:
        caller_filepath = inspect.stack()[1].filename
    except Exception:
        caller_filepath = None

    asyncio.run_coroutine_threadsafe(
        async_run_test_suite(
            test_id=id,
            test_cases=test_cases,
            evaluators=evaluators,
            fn=fn,
            max_test_case_concurrency=max_test_case_concurrency,
            caller_filepath=caller_filepath,
        ),
        global_state.event_loop(),
    ).result()
