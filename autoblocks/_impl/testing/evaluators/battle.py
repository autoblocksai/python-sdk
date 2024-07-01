import abc
import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Generic
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.testing.evaluators.util import get_autoblocks_api_key
from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.evaluators.util import get_test_id
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.util import encode_uri_component


@dataclass
class BattleResponse:
    result: str
    reason: str


threshold = Threshold(gte=0.5)  # consider a tie as passing


async def battle(baseline: str, challenger: str, criteria: str, evaluator_id: str) -> Evaluation:
    """
    Returns 0 if tie, 1 if baseline wins, 2 if challenger wins
    """
    response = await get_openai_client(evaluator_id=evaluator_id).chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            dict(
                role="system",
                content=dedent(
                    """You are an expert in comparing responses to given criteria.
                    Pick which response is the best while taking the criteria into consideration.
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
                    {criteria}

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
    battle_response = BattleResponse(
        result=parsed_content["result"],
        reason=parsed_content["reason"],
    )
    score: float = 0
    if battle_response.result == "2":
        score = 1
    elif battle_response.result == "0":
        score = 0.5

    return Evaluation(
        score=score,
        threshold=threshold,
        metadata={
            "reason": battle_response.reason,
            "baseline": baseline,
            "challenger": challenger,
            "criteria": criteria,
        },
    )


class BaseManualBattle(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The ManualBattle evaluator compares two responses based on a given criteria.
    If you would like to Autoblocks to automatically manage the baseline, use the AutomaticBattle evaluator.
    """

    threshold = Threshold(gte=0.5)  # consider a tie as passing

    @property
    @abc.abstractmethod
    def criteria(self) -> str:
        pass

    @abc.abstractmethod
    def baseline_mapper(self, test_case: TestCaseType) -> str:
        """
        Map the baseline ground truth from your test case for comparison.
        """
        pass

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map your output to a string for comparison to the baseline.
        """
        pass

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        mapped_output = self.output_mapper(output)
        baseline = self.baseline_mapper(test_case)

        return await battle(baseline=baseline, challenger=mapped_output, criteria=self.criteria, evaluator_id=self.id)


class BaseAutomaticBattle(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The AutomaticBattle evaluator compares two responses based on a given criteria.
    If the challenger wins, the challenger becomes the new baseline automatically.
    If you would like to provide your own baseline, use the ManualBattle evaluator.
    """

    @property
    @abc.abstractmethod
    def criteria(self) -> str:
        pass

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map your output to a string for comparison to the baseline.
        """
        pass

    @staticmethod
    def _make_baseline_url(test_id: str, test_case_hash: str) -> str:
        encoded_test_id = encode_uri_component(test_id)
        encoded_test_case_hash = encode_uri_component(test_case_hash)
        return f"{API_ENDPOINT}/test-suites/{encoded_test_id}/test-cases/{encoded_test_case_hash}/baseline"

    async def _get_baseline(self, test_id: str, test_case: TestCaseType) -> Optional[str]:
        # fetch the baseline from the API
        resp = await global_state.http_client().get(
            self._make_baseline_url(test_id=test_id, test_case_hash=test_case.hash()),
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        baseline = resp.json().get("baseline")
        # If this is the first time the battle evaluator has been run for this test case, there won't be a baseline
        return baseline if isinstance(baseline, str) else None

    async def _save_baseline(self, test_id: str, baseline: str, test_case_hash: str) -> None:
        resp = await global_state.http_client().post(
            self._make_baseline_url(test_id=test_id, test_case_hash=test_case_hash),
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
            json={"baseline": baseline},
        )
        resp.raise_for_status()

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Optional[Evaluation]:
        test_id = get_test_id(evaluator_id=self.id)
        mapped_output = self.output_mapper(output)
        baseline = await self._get_baseline(test_id=test_id, test_case=test_case)
        if baseline is None:
            # If there isn't an existing baseline, and the user didn't pass one in
            # Or it is the first time this evaluator is being run for this test case
            # We save the current challenger as the baseline and skip evaluating
            await self._save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())
            return None

        result = await battle(baseline=baseline, challenger=mapped_output, criteria=self.criteria, evaluator_id=self.id)
        if result.score == 1:
            # save the current challenger as the new baseline if it wins
            await self._save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case.hash())

        return result
