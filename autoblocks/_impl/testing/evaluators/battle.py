import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Callable
from typing import Generic
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.testing.evaluators.util import get_autoblocks_api_key
from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


@dataclass
class BattleResponse:
    result: str
    reason: str


class Battle(BaseTestEvaluator, Generic[TestCaseType, OutputType]):
    """
    The Battle evaluator compares two responses based on a given criteria.
    If the challenger wins, the challenger becomes the new baseline automatically.
    You can override this behavior by passing in a baseline_mapper and handling the baseline yourself.
    """

    id = "battle"

    def __init__(
        self,
        # Criteria to be used in the battle
        criteria: str,
        # Map your output to a string for comparison
        output_mapper: Callable[[OutputType], str],
        # Optional baseline_mapper allows you to store a baseline on your test case
        # Instead of having Autoblocks automatically track it
        baseline_mapper: Optional[Callable[[TestCaseType], str]] = None,
    ):
        super().__init__()
        self.output_mapper = output_mapper
        self.baseline_mapper = baseline_mapper
        self.criteria = criteria

    async def get_baseline(self, test_id: str, test_case: TestCaseType) -> Optional[str]:
        # if the user passed in a baseline_mapper, we use that
        if self.baseline_mapper:
            return self.baseline_mapper(test_case)

        # otherwise, we fetch the baseline from the API
        resp = await global_state.http_client().get(
            f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case.hash()}/baseline",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        baseline = resp.json().get("baseline")
        # If this is the first time the battle evaluator has been run for this test case, there won't be a baseline
        return baseline if isinstance(baseline, str) else None

    async def save_baseline(self, test_id: str, baseline: str, test_case_hash: str) -> None:
        resp = await global_state.http_client().post(
            f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case_hash}/baseline",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
            json={"baseline": baseline},
        )
        resp.raise_for_status()

    async def battle(self, baseline: str, challenger: str) -> BattleResponse:
        """
        Returns 0 if tie, 1 if baseline wins, 2 if challenger wins
        """
        response = await get_openai_client(evaluator_id=self.id).chat.completions.create(
            model="gpt-4-turbo",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                dict(
                    role="system",
                    content=dedent(
                        """You are an expert in comparing responses to given instructions.
                        You are comparing responses to the following criteria.
                        Pick which response is the best.
                        Return 1 if the baseline is better, 2 if the challenger is better, and 0 if they are equal.
                        You must provide one answer based on your subjective view and provide a reason for your answer.

                        Always output in the following JSON format:

                        {
                          "reason": "This is the reason.",
                          "result": "0" | "1" | "2"
                        }"""
                    ),
                ),
                dict(
                    role="user",
                    content=dedent(
                        f"""[Criteria]
                        {self.criteria}

                        [Baseline]
                        {baseline}

                        [Challenger]
                        {challenger}"""
                    ),
                ),
            ],
        )

        raw_content = response.choices[0].message.content
        if not raw_content:
            raise ValueError("No content was returned from OpenAI for the Battle evaluator")

        parsed_content = json.loads(raw_content.strip())
        return BattleResponse(
            result=parsed_content["result"],
            reason=parsed_content["reason"],
        )

    def get_test_id(self) -> str:
        """
        Retrieves the current test from the test run context
        """
        test_run_ctx = test_case_run_context_var.get()
        if test_run_ctx is None:
            # Evaluators should always be run inside the context of a test case
            raise ValueError(f"No test case context found in the {self.id} evaluator.")
        return test_run_ctx.test_id

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Optional[Evaluation]:
        test_id = self.get_test_id()
        mapped_output = self.output_mapper(output)
        baseline = await self.get_baseline(test_id=test_id, test_case=test_case)
        if baseline is None:
            # If there isn't an existing baseline, and the user didn't pass one in
            # Or it is the first time this evaluator is being run for this test case
            # We save the current challenger as the baseline and skip evaluating
            await self.save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())
            return None

        battle_result = await self.battle(
            baseline=baseline,
            challenger=mapped_output,
        )
        score: float = 0
        if battle_result.result == "2":
            # challenger wins so save the new baseline
            await self.save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())
            score = 1
        elif battle_result.result == "0":
            # tie
            score = 0.5

        return Evaluation(
            score=score,
            threshold=Threshold(gte=0.5),  # Consider a tie as passing
            metadata={"reason": battle_result.reason, "baseline": baseline, "challenger": mapped_output},
        )
