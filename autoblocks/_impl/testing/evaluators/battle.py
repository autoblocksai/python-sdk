import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Callable
from typing import Generic
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.testing.evaluators.openai_client import openai_client
from autoblocks._impl.testing.evaluators.pydantic_util import FrozenModel
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.util import AutoblocksEnvVar

autoblocks_api_key = AutoblocksEnvVar.API_KEY.get()
# The Autoblocks API key should always be set since we will be in a testing context
if not autoblocks_api_key:
    raise ValueError(f"You must set the {AutoblocksEnvVar.API_KEY} environment variable to use the Battle Evaluator.")


@dataclass
class BattleResponse:
    result: bool
    reason: str


class BaselineResponse(FrozenModel):
    baseline: Optional[str]


async def save_baseline(test_id: str, baseline: str, test_case_hash: str) -> None:
    resp = await global_state.http_client().post(
        f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case_hash}/baseline",
        headers={"Authorization": f"Bearer {autoblocks_api_key}"},
        json={"baseline": baseline},
    )
    resp.raise_for_status()


async def battle(instructions: str, baseline: str, challenger: str) -> BattleResponse:
    """
    Returns true if the challenger wins, false if the baseline wins.
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            dict(
                role="system",
                content=dedent(
                    """You are an expert in comparing responses to given instructions.
                    You are comparing responses to the following instructions.
                    Is the first response better than the second?
                    You must provide one answer based on your subjective view and provide a reason for your answer.

                    Always output in the following JSON format:

                    {
                      "reason": "This is the reason.",
                      "result": "1" | "2"
                    }"""
                ),
            ),
            dict(
                role="user",
                content=dedent(
                    f"""[Instructions]
                    {instructions}

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
        result=parsed_content["result"] == "2",
        reason=parsed_content["reason"],
    )


class Battle(BaseTestEvaluator, Generic[TestCaseType, OutputType]):
    id = "battle"

    def __init__(self, instructions: str, output_mapper: Callable[[OutputType], str], baseline: Optional[str]):
        super().__init__()
        self.output_mapper = output_mapper
        self.baseline = baseline
        self.instructions = instructions

    async def get_baseline(self, test_id: str, test_case_hash: str) -> Optional[str]:
        # if the user passed in a baseline, we use that
        if self.baseline:
            return self.baseline

        # otherwise, we fetch the baseline from the API
        resp = await global_state.http_client().get(
            f"{API_ENDPOINT}/test-suites/{test_id}/test-cases/{test_case_hash}/baseline",
            headers={"Authorization": f"Bearer {autoblocks_api_key}"},
        )
        resp.raise_for_status()
        validated = BaselineResponse.model_validate(resp.json())
        return validated.baseline

    async def evaluate_test_case(
        self, test_case: TestCaseType, output: OutputType, test_id: str, test_case_hash: str
    ) -> Optional[Evaluation]:
        baseline = await self.get_baseline(test_id=test_id, test_case_hash=test_case_hash)
        mapped_output = self.output_mapper(output)
        if baseline is None:
            # If there isn't an existing baseline, and the user didn't pass one in
            # We save the current challenger as the baseline and skip evaluating
            await save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case_hash)
            return None

        battle_result = await battle(
            instructions=self.instructions,
            baseline=baseline,
            challenger=mapped_output,
        )
        if battle_result.result:
            # save the new baseline if the challenger wins
            await save_baseline(test_id=test_id, baseline=mapped_output, test_case_hash=test_case_hash)

        score = 1 if battle_result.result else 0
        return Evaluation(
            score=score,
            threshold=Threshold(gte=1),
            metadata={"reason": battle_result.reason, "baseline": baseline, "challenger": mapped_output},
        )
