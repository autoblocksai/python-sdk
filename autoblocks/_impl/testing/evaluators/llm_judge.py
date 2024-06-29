import abc
import json
from textwrap import dedent
from typing import Any
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.testing.evaluators.util import get_autoblocks_api_key
from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.evaluators.util import get_test_id
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import EvaluatorOverride
from autoblocks._impl.testing.models import HumanReviewCommentOverride
from autoblocks._impl.testing.models import HumanReviewFieldOverride
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import ScoreChoice
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold

function_name = "select_answer"


class BaseLLMJudge(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    Base evaluator for creating a LLM judge.
    """

    @property
    @abc.abstractmethod
    def threshold(self) -> Optional[Threshold]:
        """
        The threshold for the evaluator.
        """
        pass

    @property
    def no_of_overrides(self) -> int:
        """
        The number of recent overrides to fetch for the evaluator and pass to make_prompt.

        Defaults to 0.
        """
        return 0

    @abc.abstractmethod
    def make_prompt(
        self, test_case: TestCaseType, output: OutputType, recent_overrides: List[EvaluatorOverride]
    ) -> str:
        """
        The prompt passed to the LLM judge. Should be poised as a question.
        """
        pass

    @property
    @abc.abstractmethod
    def score_choices(self) -> List[ScoreChoice]:
        """
        The choices for the LLM judge to use when answering.
        """
        pass

    def _make_score_choice(self, value: float) -> Optional[ScoreChoice]:
        return next((score for score in self.score_choices if score.value == value), None)

    async def _get_recent_overrides(self) -> List[EvaluatorOverride]:
        if self.no_of_overrides == 0:
            # don't fetch if they haven't enabled overrides
            return []
        test_id = get_test_id(evaluator_id=self.id)
        resp = await global_state.http_client().get(
            f"https://adamnolte-public-api.autoblocksinternal.com/test-suites/{test_id}/evaluators/{self.id}/human-reviews?n={self.no_of_overrides}",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        data = resp.json()
        overrides = []
        for eval_data in data:
            override_score = self._make_score_choice(eval_data["overrideScore"])
            original_score = self._make_score_choice(eval_data["originalScore"])
            if override_score is None or original_score is None:
                # If for some reason we can't find the score choice, skip this override
                # Could happen if the score choices have changed since the override was created
                continue

            overrides.append(
                EvaluatorOverride(
                    original_score=original_score,
                    override_score=override_score,
                    output_fields=[HumanReviewFieldOverride(**field) for field in eval_data["outputFields"]],
                    input_fields=[HumanReviewFieldOverride(**field) for field in eval_data["inputFields"]],
                    comments=[
                        HumanReviewCommentOverride(
                            field_id=comment["fieldId"],
                            quoted_text=comment["quotedText"],
                            comment_text=comment["commentText"],
                        )
                        for comment in eval_data["comments"]
                    ],
                )
            )

        return overrides

    def _make_tool(self) -> dict[str, Any]:
        """
        We use function calling to force the LLM to return structured JSON.

        See https://platform.openai.com/docs/guides/function-callinghttps://platform.openai.com/docs/guides/function-calling
        """
        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": "Call this function to select an answer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The reason for the answer",
                        },
                        "answer": {
                            "type": "string",
                            "description": "The answer to select",
                            "enum": [score.name for score in self.score_choices],
                        },
                    },
                    "required": ["reason", "answer"],
                },
            },
        }

    async def _execute_prompt(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        recent_overrides = await self._get_recent_overrides()
        prompt = dedent(self.make_prompt(test_case=test_case, output=output, recent_overrides=recent_overrides))
        response = await get_openai_client(evaluator_id=self.id).chat.completions.create(
            model="gpt-4-turbo",
            temperature=0.0,
            tool_choice={"type": "function", "function": {"name": function_name}},
            tools=[self._make_tool()],
            messages=[
                dict(
                    role="system",
                    content=dedent(
                        """Answer the following question by selecting an answer.
                            Always provide a reason for your answer."""
                    ),
                ),
                dict(role="user", content=prompt),
            ],
        )
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name != function_name:
            # This shouldn't happen since we force the LLM to call our function, but we check just in case
            raise ValueError(f"Unexpected tool call: {tool_call}")

        function_args = json.loads(tool_call.function.arguments)

        # We should always be able to find the score choice since we set the scores as an enum in the tool
        score = next((score for score in self.score_choices if score.name == function_args["answer"]), None)
        if score is None:
            raise ValueError(f"Unexpected answer: {function_args['answer']}")

        return Evaluation(
            score=score.value,
            threshold=self.threshold,
            metadata={
                "reason": function_args["reason"],
                "prompt": prompt,
            },
        )

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        return await self._execute_prompt(test_case=test_case, output=output)