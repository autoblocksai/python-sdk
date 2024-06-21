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
    id = "battle"

    def __init__(
        self,
        criteria: str,
        output_mapper: Callable[[OutputType], str],
        baseline_mapper: Optional[Callable[[TestCaseType], str]] = None,
        evaluator_id: Optional[str] = None,
    ):
        super().__init__()
        self.output_mapper = output_mapper
        self.baseline_mapper = baseline_mapper
        self.criteria = criteria
        if evaluator_id:
            self.id = evaluator_id

    async def get_baseline(self, test_id: str, test_case: TestCaseType) -> Optional[str]:
        # if the user passed in a baseline, we use that
        if self.baseline_mapper:
            return self.baseline_mapper(test_case)

        # otherwise, we fetch the baseline from the API
        resp = await global_state.http_client().get(
            f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case.hash()}/baseline",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        baseline = resp.json().get("baseline")
        return baseline if baseline else None

    async def save_baseline(self, test_id: str, baseline: str, test_case_hash: str) -> None:
        resp = await global_state.http_client().post(
            f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case_hash}/baseline",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
            json={"baseline": baseline},
        )
        resp.raise_for_status()

    async def battle(self, baseline: str, challenger: str) -> BattleResponse:
        """
        Returns true if the challenger wins, false if the baseline wins.
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
                        You are comparing responses to the following instructions.
                        Pick which response is the best. If they are equally good, you can set the result to 0.
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

                        [Response 1]
                        {baseline}

                        [Response 2]
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

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Optional[Evaluation]:
        test_run_ctx = test_case_run_context_var.get()
        if test_run_ctx is None:
            raise ValueError("No test case context found in the Battle evaluator.")
        test_id = test_run_ctx.test_id
        baseline = await self.get_baseline(test_id=test_id, test_case=test_case)
        mapped_output = self.output_mapper(output)
        if baseline is None:
            # If there isn't an existing baseline, and the user didn't pass one in
            # We save the current challenger as the baseline and skip evaluating
            await self.save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())
            return None

        battle_result = await self.battle(
            baseline=baseline,
            challenger=mapped_output,
        )
        score: float = 0

        if battle_result.result == "2":
            # save the new baseline if the challenger wins
            await self.save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())
            score = 1
        elif battle_result.result == "0":
            # tie
            score = 0.5

        return Evaluation(
            score=score,
            threshold=Threshold(gte=0.5),
            metadata={"reason": battle_result.reason, "baseline": baseline, "challenger": mapped_output},
        )
