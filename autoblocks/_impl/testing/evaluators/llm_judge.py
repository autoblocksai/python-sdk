import abc
import json
import re
from textwrap import dedent
from typing import Generic
from typing import List

from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import ScoreChoice
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold

override_template = """
================
Example:
Output: {{ output }}
Answer: {{ answer }}
"""


def replace_with_values(template: str, replacements: dict[str, str]) -> str:
    # Regex to find {{ key }} even with irregular spaces
    pattern = r"\{\{\s*(\w+)\s*\}\}"
    # Replace each found key with the corresponding value from the replacements dictionary
    result = re.sub(pattern, lambda match: replacements.get(match.group(1), match.group(0)), template)
    return result


class BaseLLMJudge(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):

    @property
    @abc.abstractmethod
    def threshold(self) -> Threshold:
        pass

    @property
    @abc.abstractmethod
    def prompt(self) -> str:
        pass

    @property
    def use_overrides(self) -> bool:
        return False

    @property
    @abc.abstractmethod
    def score_choices(self) -> List[ScoreChoice]:
        pass

    @abc.abstractmethod
    def variable_mapper(self, test_case: TestCaseType, output: OutputType) -> dict[str, str]:
        pass

    async def make_prompt(self, test_case: TestCaseType, output: OutputType) -> str:
        replacements = self.variable_mapper(test_case=test_case, output=output)
        template_with_values = replace_with_values(template=self.prompt, replacements=replacements)
        if self.use_overrides:
            overrides = await self.get_recent_overrides()
            if overrides is not None:
                override_choice = next(
                    (score for score in self.score_choices if score.value == overrides.override_score), None
                )
                if override_choice is not None:
                    template_with_values += replace_with_values(
                        template=override_template,
                        replacements={"output": overrides.output_fields[0].value, "answer": override_choice.name},
                    )

        return dedent(template_with_values)

    async def execute_prompt(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        prompt = await self.make_prompt(test_case=test_case, output=output)
        response = await get_openai_client(evaluator_id=self.id).chat.completions.create(
            model="gpt-4-turbo",
            temperature=0.0,
            tool_choice={"type": "function", "function": {"name": "select_answer"}},
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "select_answer",
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
            ],
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
        if tool_call.function.name != "select_answer":
            raise ValueError(f"Unexpected tool call: {tool_call}")

        function_args = json.loads(tool_call.function.arguments)
        score = next((score for score in self.score_choices if score.name == function_args["answer"]), None)
        if score is None:
            raise ValueError(f"Unexpected score: {function_args['answer']}")

        return Evaluation(
            score=score.value,
            threshold=self.threshold,
            metadata={
                "reason": function_args["reason"],
                "prompt": prompt,
            },
        )

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        return await self.execute_prompt(test_case=test_case, output=output)
