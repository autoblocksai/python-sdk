import asyncio
import contextvars
import dataclasses
import inspect
import traceback
from typing import Any
from typing import Callable
from typing import List
from typing import Optional

import httpx
import orjson

from autoblocks._impl import global_state
from autoblocks._impl.testing.models import BaseEvaluator
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import gather_with_max_concurrency

# Global httpx client
client: httpx.AsyncClient = None

# Context
current_test_id_var = contextvars.ContextVar("current_test_id")
current_test_case_var = contextvars.ContextVar("current_test_case")


def init_client():
    global client
    if client is None:
        cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
        if not cli_server_address:
            raise RuntimeError(
                "Autoblocks tests must be run within the context of the testing CLI.\n"
                "Make sure you are running your test command with:\n"
                "$ npx autoblocks testing exec -- <your test command>"
            )
        client = httpx.AsyncClient(base_url=cli_server_address)


def orjson_default(o: Any) -> str:
    if hasattr(o, "model_dump_json") and callable(o.model_dump_json):
        # pydantic v2
        return orjson.loads(o.model_dump_json())
    elif hasattr(o, "json") and callable(o.json):
        # pydantic v1
        return orjson.loads(o.json())
    raise TypeError


def serialize(x: Any) -> Any:
    return orjson.loads(orjson.dumps(x, default=orjson_default))


async def send_error(
    test_id: str,
    test_case_hash: Optional[str],
    evaluator_id: Optional[str],
    error: Exception,
) -> None:
    await client.post(
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


async def evaluate_output(
    test_id: str,
    test_case: BaseTestCase,
    output: Any,
    evaluator: BaseEvaluator,
):
    evaluation: Optional[Evaluation] = None

    if inspect.iscoroutinefunction(evaluator.evaluate):
        try:
            evaluation = await evaluator.evaluate(test_case, output)
        except Exception as err:
            await send_error(
                test_id=test_id,
                test_case_hash=test_case._cached_hash,
                evaluator_id=evaluator.id,
                error=err,
            )
    else:
        try:
            ctx = contextvars.copy_context()
            evaluation = await global_state.event_loop().run_in_executor(
                None,
                ctx.run,
                evaluator.evaluate,
                test_case,
                output,
            )
        except Exception as err:
            await send_error(
                test_id=test_id,
                test_case_hash=test_case._cached_hash,
                evaluator_id=evaluator.id,
                error=err,
            )

    if evaluation is None:
        return

    await client.post(
        "/evals",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case._cached_hash,
            evaluatorExternalId=evaluator.id,
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
        ),
    )


async def run_test_case(
    test_id: str,
    test_case: BaseTestCase,
    evaluators: List[BaseEvaluator],
    fn: Callable,
    max_evaluator_concurrency: int,
):
    current_test_id_var.set(test_id)
    current_test_case_var.set(test_case)

    output = None

    if inspect.iscoroutinefunction(fn):
        try:
            output = await fn(test_case)
        except Exception as err:
            await send_error(
                test_id=test_id,
                test_case_hash=test_case._cached_hash,
                evaluator_id=None,
                error=err,
            )
    else:
        try:
            ctx = contextvars.copy_context()
            output = await global_state.event_loop().run_in_executor(None, ctx.run, fn, test_case)
        except Exception as err:
            await send_error(
                test_id=test_id,
                test_case_hash=test_case._cached_hash,
                evaluator_id=None,
                error=err,
            )

    if output is None:
        return

    await client.post(
        "/results",
        json=dict(
            testExternalId=test_id,
            testCaseHash=test_case._cached_hash,
            testCaseBody=serialize(test_case),
            testCaseOutput=serialize(output),
        ),
    )

    try:
        await gather_with_max_concurrency(
            max_evaluator_concurrency,
            [
                evaluate_output(
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


async def async_run_test_suite(
    test_id: str,
    test_cases: List[BaseTestCase],
    evaluators: List[BaseEvaluator],
    fn: Callable,
    max_test_case_concurrency: int,
    max_evaluator_concurrency: int,
):
    try:
        assert test_cases, f"[{test_id}] No test cases provided."
        for test_case in test_cases:
            assert isinstance(
                test_case,
                BaseTestCase,
            ), f"[{test_id}] Test case {test_case} does not implement BaseTestCase."
        for evaluator in evaluators:
            assert isinstance(
                evaluator,
                BaseEvaluator,
            ), f"[{test_id}] Evaluator {evaluator} does not implement BaseEvaluator."
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=None,
            evaluator_id=None,
            error=err,
        )
        return

    await client.post("/start", json=dict(testExternalId=test_id))

    try:
        await gather_with_max_concurrency(
            max_test_case_concurrency,
            [
                run_test_case(
                    test_id=test_id,
                    test_case=test_case,
                    evaluators=evaluators,
                    fn=fn,
                    max_evaluator_concurrency=max_evaluator_concurrency,
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

    await client.post("/end", json=dict(testExternalId=test_id))


def run_test_suite(
    id: str,
    test_cases: List[BaseTestCase],
    evaluators: List[BaseEvaluator],
    fn: Callable,
    # How many test cases to run concurrently
    max_test_case_concurrency: int = 10,
    # How many evaluators to run concurrently on the result of a test case
    max_evaluator_concurrency: int = 5,
):
    init_client()
    global_state.init()
    future = asyncio.run_coroutine_threadsafe(
        async_run_test_suite(
            test_id=id,
            test_cases=test_cases,
            evaluators=evaluators,
            fn=fn,
            max_test_case_concurrency=max_test_case_concurrency,
            max_evaluator_concurrency=max_evaluator_concurrency,
        ),
        global_state.event_loop(),
    )
    future.result()
