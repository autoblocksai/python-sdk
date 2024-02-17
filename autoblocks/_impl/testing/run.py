import asyncio
import contextvars
import dataclasses
import inspect
import threading
import traceback
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import List
from typing import Optional

import httpx

from autoblocks._impl.testing.models import BaseEvaluator
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.util import AutoblocksEnvVar

# Globals
client: httpx.AsyncClient = None
loop: asyncio.AbstractEventLoop = None
started: bool = False


# Context
current_test_id_var = contextvars.ContextVar("current_test_id")
current_test_case_var = contextvars.ContextVar("current_test_case")


def run_event_loop(_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def init_global_vars() -> None:
    global client, loop, started

    if started:
        return

    cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
    if not cli_server_address:
        raise RuntimeError(
            "Autoblocks tests must be run within the context of the testing CLI.\n"
            "Make sure you are running your test command with:\n"
            "$ npx autoblocks testing exec -- <your test command>"
        )
    client = httpx.AsyncClient(base_url=cli_server_address)

    loop = asyncio.new_event_loop()

    background_thread = threading.Thread(
        target=run_event_loop,
        args=(loop,),
        daemon=True,
    )
    background_thread.start()

    started = True


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


async def gather_with_max_concurrency(
    max_concurrency: int,
    *coroutines: Coroutine,
) -> None:
    """
    Borrowed from https://stackoverflow.com/a/61478547
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_coro(coro: Coroutine):
        async with semaphore:
            return await coro

    # return_exceptions=True causes exceptions to be returned as values instead
    # of propagating them to the caller. this is similar in behavior to Promise.allSettled
    await asyncio.gather(*(sem_coro(c) for c in coroutines), return_exceptions=True)


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
            evaluation = await loop.run_in_executor(
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
            output = await loop.run_in_executor(None, ctx.run, fn, test_case)
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
            testCaseBody=dataclasses.asdict(test_case),
            testCaseOutput=output,
        ),
    )

    await gather_with_max_concurrency(
        max_evaluator_concurrency,
        *[
            evaluate_output(
                test_id=test_id,
                test_case=test_case,
                output=output,
                evaluator=evaluator,
            )
            for evaluator in evaluators
        ],
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
            assert isinstance(test_case, BaseTestCase), (
                f"[{test_id}] Test case {test_case} does not implement " f"BaseTestCase."
            )
        for evaluator in evaluators:
            assert isinstance(evaluator, BaseEvaluator), (
                f"[{test_id}] Evaluator {evaluator} does not implement " "BaseEvaluator."
            )
    except Exception as err:
        await send_error(
            test_id=test_id,
            test_case_hash=None,
            evaluator_id=None,
            error=err,
        )
        return

    await client.post("/start", json=dict(testExternalId=test_id))

    await gather_with_max_concurrency(
        max_test_case_concurrency,
        *[
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
    init_global_vars()

    future = asyncio.run_coroutine_threadsafe(
        async_run_test_suite(
            test_id=id,
            test_cases=test_cases,
            evaluators=evaluators,
            fn=fn,
            max_test_case_concurrency=max_test_case_concurrency,
            max_evaluator_concurrency=max_evaluator_concurrency,
        ),
        loop,
    )
    future.result()
