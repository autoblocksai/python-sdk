import abc
import asyncio
import logging
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.testing.api import send_create_human_review_job
from autoblocks._impl.testing.api import send_end_test_run
from autoblocks._impl.testing.api import send_eval
from autoblocks._impl.testing.api import send_start_test_run
from autoblocks._impl.testing.api import send_test_case_result
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import EvaluationWithId
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType

log = logging.getLogger(__name__)


class RunManager(abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RunManager class can be used to manually manage the lifecycle of a test suite.
    You can also use `runTestSuite` for a more feature rich, managed experience.
    """

    def __init__(
        self,
        test_id: str,
        message: Optional[str] = None,
    ):
        self.test_external_id = test_id
        self.message = message
        self.run_id: Optional[str] = None
        self.ended = False

        global_state.init()

    async def async_start(self) -> None:
        """
        Starts the run. This must be called before any test case results are added to the run.
        """
        self.run_id = await send_start_test_run(
            test_external_id=self.test_external_id,
            message=self.message,
            grid_search_run_group_id=None,
            grid_search_params_combo=None,
        )

    def start(self) -> None:
        """
        Starts the run. This must be called before any test case results are added to the run.
        """
        asyncio.run_coroutine_threadsafe(self.async_start(), global_state.event_loop()).result()

    async def async_add_result(
        self,
        test_case: TestCaseType,
        output: OutputType,
        test_case_duration_ms: Optional[float] = None,
        evaluations: Optional[List[EvaluationWithId]] = None,
    ) -> None:
        """
        Adds a test case, its output, and evaluations to the run.
        """
        if not self.run_id:
            raise ValueError("You must start the run with `start()` before adding results.")
        if self.ended:
            raise ValueError("You cannot add results to an ended run.")

        test_case_ctx = TestCaseContext(test_case=test_case, repetition_idx=None)

        test_case_result_id = await send_test_case_result(
            test_external_id=self.test_external_id,
            run_id=self.run_id,
            test_case_ctx=test_case_ctx,
            output=output,
            test_case_duration_ms=test_case_duration_ms or 0,
        )

        if not evaluations:
            return

        for evaluation in evaluations:
            try:
                await send_eval(
                    test_external_id=self.test_external_id,
                    run_id=self.run_id,
                    test_case_hash=test_case_ctx.hash(),
                    evaluator_external_id=evaluation.id,
                    evaluation=Evaluation(
                        score=evaluation.score,
                        threshold=evaluation.threshold,
                        metadata=evaluation.metadata,
                        assertions=evaluation.assertions,
                    ),
                    test_case_result_id=test_case_result_id,
                )
            except Exception as e:
                log.warning(f"Failed to send evaluation to Autoblocks for test case hash {test_case_ctx.hash()}: {e}")

    def add_result(
        self,
        test_case: TestCaseType,
        output: OutputType,
        test_case_duration_ms: Optional[float] = None,
        evaluations: Optional[List[EvaluationWithId]] = None,
    ) -> None:
        """
        Adds a test case, its output, and evaluations to the run.
        """
        asyncio.run_coroutine_threadsafe(
            self.async_add_result(
                test_case=test_case, output=output, test_case_duration_ms=test_case_duration_ms, evaluations=evaluations
            ),
            global_state.event_loop(),
        ).result()

    async def async_create_human_review_job(self, assignee_email_address: str, name: str) -> None:
        """
        Creates a new human review job that includes the test case results that have been added to the run.
        """
        if not self.run_id:
            raise ValueError("You must start the run with `start()` before creating a human review job.")

        await send_create_human_review_job(run_id=self.run_id, assignee_email_address=assignee_email_address, name=name)

    def create_human_review_job(self, assignee_email_address: str, name: str) -> None:
        """
        Creates a new human review job that includes the test case results that have been added to the run.
        """
        asyncio.run_coroutine_threadsafe(
            self.async_create_human_review_job(assignee_email_address=assignee_email_address, name=name),
            global_state.event_loop(),
        ).result()

    async def async_end(self) -> None:
        """
        Ends the run.
        """
        if not self.run_id:
            raise ValueError("You must start the run with `start()` before ending it.")

        await send_end_test_run(test_external_id=self.test_external_id, run_id=self.run_id)
        self.ended = True

    def end(self) -> None:
        """
        Ends the run.
        """
        asyncio.run_coroutine_threadsafe(self.async_end(), global_state.event_loop()).result()
