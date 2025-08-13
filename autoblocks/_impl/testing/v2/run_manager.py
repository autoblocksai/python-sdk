import asyncio
import json
import logging
from typing import Any
from typing import List
from typing import Optional
from typing import Sequence

from autoblocks._impl import global_state
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import EvaluationWithId
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.util import serialize_output
from autoblocks._impl.testing.util import serialize_test_case
from autoblocks._impl.testing.v2.api import send_create_human_review_job
from autoblocks._impl.testing.v2.api import send_create_result
from autoblocks._impl.testing.v2.run import evaluator_semaphore_registry
from autoblocks._impl.testing.v2.run import run_evaluator
from autoblocks._impl.util import all_settled
from autoblocks._impl.util import cuid_generator
from autoblocks._impl.util import now_rfc3339

log = logging.getLogger(__name__)


class RunManager:
    """
    Manual-only run manager for V2.

    Lifecycle:
      - start(): mark start timestamp (no network)
      - add_result(): compute evaluations locally, POST a single composite result
      - end(): mark end timestamp and allow human review creation
      - create_human_review(): create HR job using start/end timestamps
    """

    def __init__(self, app_slug: str, environment: str = "test", run_message: Optional[str] = None):
        self.app_slug = app_slug
        self.environment = environment
        self.run_message = run_message

        self.run_id: str = cuid_generator()
        self.started_at: Optional[str] = None
        self.ended_at: Optional[str] = None
        self.can_create_human_review: bool = False

    async def async_start(self) -> None:
        global_state.init()
        self.started_at = now_rfc3339()

    def start(self) -> None:
        global_state.init()
        asyncio.run_coroutine_threadsafe(self.async_start(), global_state.event_loop()).result()

    async def _compute_evaluations(
        self,
        *,
        test_case_ctx: TestCaseContext[BaseTestCase],
        output: Any,
        evaluators: Optional[Sequence[BaseTestEvaluator]],
    ) -> List[EvaluationWithId]:
        if not evaluators:
            return []

        # Ensure evaluator semaphore registry is initialized for manual V2 runs
        # using app_slug as the test suite identifier.
        reg = evaluator_semaphore_registry.get(self.app_slug)
        if reg is None:
            evaluator_semaphore_registry[self.app_slug] = {
                evaluator.id: asyncio.Semaphore(evaluator.max_concurrency) for evaluator in evaluators
            }
        else:
            for evaluator in evaluators:
                if evaluator.id not in reg:
                    reg[evaluator.id] = asyncio.Semaphore(evaluator.max_concurrency)
        results = await all_settled(
            [
                run_evaluator(
                    test_id=self.app_slug,  # use app_slug as the suite identifier for semaphore scoping
                    test_case_ctx=test_case_ctx,
                    output=output,
                    hook_results=None,
                    evaluator=evaluator,
                )
                for evaluator in evaluators
            ]
        )

        evaluations: List[EvaluationWithId] = []
        for value in results:
            if isinstance(value, EvaluationWithId):
                evaluations.append(value)
            elif isinstance(value, Exception):
                log.error("Evaluator execution failed", exc_info=value)
        return evaluations

    @staticmethod
    def _evaluations_to_maps(
        evals: List[EvaluationWithId],
    ) -> tuple[dict[str, bool], dict[str, str], dict[str, float]]:
        id_to_result: dict[str, bool] = {}
        id_to_reason: dict[str, str] = {}
        id_to_score: dict[str, float] = {}

        for e in evals:
            # Reconstruct Evaluation to compute passed()
            evaluation = Evaluation(
                score=e.score,
                threshold=e.threshold,
                metadata=e.metadata,
                assertions=e.assertions,
            )

            # Passed/failed
            # Evaluation.passed() may be None if no threshold comparisons apply; coerce to bool for API
            id_to_result[e.id] = bool(evaluation.passed())

            # Reason selection: metadata.reason > first failing assertion > ''
            reason: str = ""

            if evaluation.metadata and isinstance(evaluation.metadata, dict):
                maybe_reason = evaluation.metadata.get("reason")

                if isinstance(maybe_reason, str) and maybe_reason:
                    reason = maybe_reason
            if not reason and evaluation.assertions:
                for a in evaluation.assertions:
                    if not a.passed:
                        # V2 Assertion has no `message` attribute; prefer metadata fields if present
                        metadata = a.metadata or {}
                        maybe_msg = metadata.get("message") or metadata.get("reason")
                        reason = maybe_msg if isinstance(maybe_msg, str) else ""
                        if reason:
                            break

            id_to_reason[e.id] = reason
            id_to_score[e.id] = e.score
        return id_to_result, id_to_reason, id_to_score

    async def async_add_result(
        self,
        *,
        test_case: BaseTestCase,
        output: Any,
        duration_ms: float,
        evaluators: Optional[Sequence[BaseTestEvaluator]] = None,
        status: str = "SUCCESS",
        started_at: Optional[str] = None,
    ) -> str:
        if self.ended_at:
            raise ValueError("You cannot add results to an ended run.")

        global_state.init()
        # Build test case context
        test_case_ctx = TestCaseContext(test_case=test_case, repetition_idx=None)

        # Compute evaluations like the OTEL path
        evals = await self._compute_evaluations(
            test_case_ctx=test_case_ctx,
            output=output,
            evaluators=evaluators or [],
        )
        eval_result_map, eval_reason_map, eval_score_map = self._evaluations_to_maps(evals)

        # Serialize input/output with standard json to match expected formatting in tests
        input_raw = json.dumps(serialize_test_case(test_case))
        output_raw = json.dumps(serialize_output(output))

        # Per-execution start time defaults to now if not provided
        exec_started_at = started_at or now_rfc3339()

        # POST composite result
        resp = await send_create_result(
            app_slug=self.app_slug,
            run_id=self.run_id,
            environment=self.environment,
            started_at=exec_started_at,
            duration_ms=duration_ms,
            status=status,
            input_raw=input_raw,
            output_raw=output_raw,
            input_map=json.loads(input_raw),
            output_map=json.loads(output_raw),
            evaluator_id_to_result=eval_result_map,
            evaluator_id_to_reason=eval_reason_map,
            evaluator_id_to_score=eval_score_map,
            run_message=self.run_message,
        )
        data = resp.json()
        execution_id = data["executionId"]
        # Ensure we return a string
        return str(execution_id)

    def add_result(
        self,
        *,
        test_case: BaseTestCase,
        output: Any,
        duration_ms: float,
        evaluators: Optional[Sequence[BaseTestEvaluator]] = None,
        status: str = "SUCCESS",
        metadata: Optional[dict[str, str]] = None,
        started_at: Optional[str] = None,
    ) -> str:
        return asyncio.run_coroutine_threadsafe(
            self.async_add_result(
                test_case=test_case,
                output=output,
                duration_ms=duration_ms,
                evaluators=evaluators,
                status=status,
                started_at=started_at,
            ),
            global_state.event_loop(),
        ).result()

    async def async_end(self) -> None:
        if not self.started_at:
            # Still allow end(), but set a start timestamp to keep HR window valid
            self.started_at = now_rfc3339()
        self.ended_at = now_rfc3339()
        self.can_create_human_review = True

    def end(self) -> None:
        asyncio.run_coroutine_threadsafe(self.async_end(), global_state.event_loop()).result()

    async def async_create_human_review(
        self,
        *,
        name: str,
        assignee_email_addresses: List[str],
        rubric_id: Optional[str] = None,
    ) -> None:
        if not self.can_create_human_review or not self.started_at or not self.ended_at:
            raise ValueError("Run has not ended or timestamps missing; call end() before creating human review.")

        await send_create_human_review_job(
            run_id=self.run_id,
            app_slug=self.app_slug,
            start_timestamp=self.started_at,
            end_timestamp=self.ended_at,
            assignee_email_addresses=assignee_email_addresses,
            name=name,
            rubric_id=rubric_id,
        )

    def create_human_review(
        self,
        *,
        name: str,
        assignee_email_addresses: List[str],
        rubric_id: Optional[str] = None,
    ) -> None:
        asyncio.run_coroutine_threadsafe(
            self.async_create_human_review(
                name=name,
                assignee_email_addresses=assignee_email_addresses,
                rubric_id=rubric_id,
            ),
            global_state.event_loop(),
        ).result()
