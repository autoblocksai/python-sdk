import asyncio
import contextvars
import dataclasses
import inspect
import logging
import traceback
from typing import Any
from typing import Callable
from typing import List
from typing import Optional

import orjson

from autoblocks._impl import global_state
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled

log = logging.getLogger(__name__)

test_case_semaphore_registry: dict[str, asyncio.Semaphore] = {}  # test_id -> semaphore
evaluator_semaphore_registry: dict[str, dict[str, asyncio.Semaphore]] = {}  # test_id -> evaluator_id -> semaphore


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


def orjson_default(o: Any) -> Any:
    if hasattr(o, "model_dump_json") and callable(o.model_dump_json):
        # pydantic v2
        return orjson.loads(o.model_dump_json())
    elif hasattr(o, "json") and callable(o.json):
        # pydantic v1
        return orjson.loads(o.json())
    raise TypeError


def serialize(x: Any) -> Any:
    return orjson.loads(orjson.dumps(x, default=orjson_default))


def serialize_test_case(test_case: BaseTestCase) -> Any:
    # See https://docs.python.org/3/library/dataclasses.html#dataclasses.is_dataclass:
    # isinstance(test_case, type) checks test_case is an instance and not a type
    if dataclasses.is_dataclass(test_case) and not isinstance(test_case, type):
        serialized: dict[Any, Any] = {}
        for k, v in dataclasses.asdict(test_case).items():
            try:
                serialized[k] = serialize(v)
            except Exception:
                # Skip over non-serializable test case attributes
                pass
        return serialized

    return serialize(test_case)


async def send_error(
    test_id: str,
    test_case_hash: Optional[str],
    evaluator_id: Optional[str],
    error: Exception,
) -> None:
    await global_state.http_client().post(
        f"{cli()}/errors",
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
    test_case: BaseTestCase,
    output: Any,
    evaluator: BaseTestEvaluator,
) -> Evaluation:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    async with evaluator_semaphore_registry[test_id][evaluator.id]:
        if inspect.iscoroutinefunction(evaluator.evaluate_test_case):
            # mypy for some reason doesn't recognize that the return type of evaluate_test_case
            # is an Evaluation
            return await evaluator.evaluate_test_case(test_case, output)  # type: ignore
        else:
            ctx = contextvars.copy_context()
            return await global_state.event_loop().run_in_executor(
                None,
                ctx.run,
                evaluator.evaluate_test_case,
                test_case,
                output,
            )


async def run_evaluator(
    test_id: str,
    test_case: BaseTestCase,
    output: Any,
    evaluator: BaseTestEvaluator,
) -> None:
    try:
        evaluation = await run_evaluator_unsafe(
            test_id=test_id,
            test_case=test_case,
            output=output,
            evaluator=evaluator,
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case._cached_hash,
            evaluator_id=evaluator.id,
            error=err,
        )
        return

    await global_state.http_client().post(
        f"{cli()}/evals",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case._cached_hash,
            evaluatorExternalId=evaluator.id,
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
            metadata=evaluation.metadata,
        ),
    )


async def run_test_case_unsafe(
    test_id: str,
    test_case: BaseTestCase,
    fn: Callable[[BaseTestCase], Any],
) -> Any:
    """
    This is suffixed with _unsafe because it doesn't handle exceptions.
    Its caller will catch and handle all exceptions.
    """
    async with test_case_semaphore_registry[test_id]:
        if inspect.iscoroutinefunction(fn):
            return await fn(test_case)
        else:
            ctx = contextvars.copy_context()
            return await global_state.event_loop().run_in_executor(None, ctx.run, fn, test_case)


async def run_test_case(
    test_id: str,
    test_case: BaseTestCase,
    evaluators: List[BaseTestEvaluator],
    fn: Callable[[BaseTestCase], Any],
) -> None:
    try:
        output = await run_test_case_unsafe(
            test_id=test_id,
            test_case=test_case,
            fn=fn,
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case._cached_hash,
            evaluator_id=None,
            error=err,
        )
        return

    await global_state.http_client().post(
        f"{cli()}/results",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case._cached_hash,
            testCaseBody=serialize_test_case(test_case),
            testCaseOutput=serialize(output),
        ),
    )

    try:
        await all_settled(
            [
                run_evaluator(
                    test_id=test_id,
                    test_case=test_case,
                    output=output,
                    evaluator=evaluator,
                )
                for evaluator in evaluators
            ],
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=test_case._cached_hash,
            evaluator_id=None,
            error=err,
        )


def validate_test_suite_inputs(
    test_id: str,
    test_cases: List[BaseTestCase],
    evaluators: List[BaseTestEvaluator],
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


async def async_run_test_suite(
    test_id: str,
    test_cases: List[BaseTestCase],
    evaluators: List[BaseTestEvaluator],
    fn: Callable[[BaseTestCase], Any],
    max_test_case_concurrency: int,
) -> None:
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

    await global_state.http_client().post(f"{cli()}/start", json=dict(testExternalId=test_id))

    try:
        await all_settled(
            [
                run_test_case(
                    test_id=test_id,
                    test_case=test_case,
                    evaluators=evaluators,
                    fn=fn,
                )
                for test_case in test_cases
            ],
        )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=None,
            evaluator_id=None,
            error=err,
        )

    await global_state.http_client().post(f"{cli()}/end", json=dict(testExternalId=test_id))


def run_test_suite(
    id: str,
    test_cases: List[BaseTestCase],
    evaluators: List[BaseTestEvaluator],
    fn: Callable[[BaseTestCase], Any],
    # How many test cases to run concurrently
    max_test_case_concurrency: int = 10,
    # Deprecated arguments, but left for backwards compatibility
    max_evaluator_concurrency: Optional[int] = None,
) -> None:
    global_state.init()

    if max_evaluator_concurrency is not None:
        log.warning(
            "`max_evaluator_concurrency` is deprecated and will be removed in a future release.\n"
            "Its value is being ignored.\n"
            "Set the `max_concurrency` attribute on the evaluator class instead.\n"
            "See https://docs.autoblocks.ai/testing/sdks for more information."
        )

    asyncio.run_coroutine_threadsafe(
        async_run_test_suite(
            test_id=id,
            test_cases=test_cases,
            evaluators=evaluators,
            fn=fn,
            max_test_case_concurrency=max_test_case_concurrency,
        ),
        global_state.event_loop(),
    ).result()
