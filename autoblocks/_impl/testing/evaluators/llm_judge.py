import abc
import json
from textwrap import dedent
from typing import Any
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.testing.evaluators.util import get_autoblocks_api_key
from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.evaluators.util import get_test_id
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import EvaluationOverride
from autoblocks._impl.testing.models import EvaluationOverrideComment
from autoblocks._impl.testing.models import EvaluationOverrideField
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import ScoreChoice
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.util import encode_uri_component

function_name = "select_answer"


class BaseLLMJudge(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    Base evaluator for creating an LLM judge.
    """

    @property
    def threshold(self) -> Optional[Threshold]:
        """
        The threshold for the evaluator.
        """
        return None

    @property
    def model(self) -> str:
        """
        The model to use for the evaluator.
        It must be an OpenAI model that supports tools.
        Defaults to "gpt-4-turbo".
        """
        return "gpt-4-turbo"

    @property
    def num_overrides(self) -> int:
        """
        The number of recent evaluation overrides to fetch for the evaluator and pass to make_prompt.

        Defaults to 0.
        """
        return 0

    @property
    @abc.abstractmethod
    def score_choices(self) -> List[ScoreChoice]:
        """
        The choices for the LLM judge to use when answering.
        """
        pass

    @abc.abstractmethod
    def make_prompt(
        self, test_case: TestCaseType, output: OutputType, recent_overrides: List[EvaluationOverride]
    ) -> str:
        """
        The prompt passed to the LLM judge. Should be poised as a question.
        """
        pass

    def _find_score_choice_from_value(self, value: float) -> Optional[ScoreChoice]:
        """
        Find the score choice from choices based the float value.
        """
        return next((score for score in self.score_choices if score.value == value), None)

    def _make_recent_overrides_url(self) -> str:
        test_id = get_test_id(evaluator_id=self.id)
        encoded_test_id = encode_uri_component(test_id)
        encoded_evaluator_id = encode_uri_component(self.id)
        url = f"{API_ENDPOINT}/test-suites/{encoded_test_id}/evaluators/{encoded_evaluator_id}/human-reviews"
        return f"{url}?n={self.num_overrides}"

    async def _get_recent_overrides(self) -> List[EvaluationOverride]:
        if self.num_overrides == 0:
            # Don't fetch if the consumer hasn't requested any overrides
            return []

        resp = await global_state.http_client().get(
            self._make_recent_overrides_url(),
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        data = resp.json()
        overrides = []
        for eval_data in data:
            override_score = self._find_score_choice_from_value(eval_data["overrideScore"])
            original_score = self._find_score_choice_from_value(eval_data["originalScore"])
            if override_score is None or original_score is None:
                # If for some reason we can't find the score choice, skip this override
                # Could happen if the score choices have changed since the override was created
                continue

            overrides.append(
                EvaluationOverride(
                    original_score=original_score,
                    override_score=override_score,
                    output_fields=[EvaluationOverrideField(**field) for field in eval_data["outputFields"]],
                    input_fields=[EvaluationOverrideField(**field) for field in eval_data["inputFields"]],
                    comments=[
                        EvaluationOverrideComment(
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

        See https://platform.openai.com/docs/guides/function-calling
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
        prompt = self.make_prompt(test_case=test_case, output=output, recent_overrides=recent_overrides)
        response = await get_openai_client(evaluator_id=self.id).chat.completions.create(
            model=self.model,
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
