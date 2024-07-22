import abc
from textwrap import dedent
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl.testing.evaluators.llm_judge import BaseLLMJudge
from autoblocks._impl.testing.models import EvaluationOverride
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import ScoreChoice
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseAccuracy(BaseLLMJudge[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The Accuracy evaluator checks if the output is accurate compared to an expected output.

    Scores 1 if the output is accurate, 0.5 if somewhat accurate, 0 otherwise.
    """

    score_choices = [
        ScoreChoice(value=1, name="Accurate"),
        ScoreChoice(value=0.5, name="Somewhat accurate"),
        ScoreChoice(value=0, name="Not accurate"),
    ]
    threshold = Threshold(gte=1)

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map the output to a string to pass to the LLM judge.
        """
        pass

    @abc.abstractmethod
    def expected_output_mapper(self, test_case: TestCaseType) -> str:
        """
        Map the test_case to an expected string to pass to the LLM judge.
        """
        pass

    def example_output_mapper(self, evaluation_override: EvaluationOverride) -> Optional[str]:
        """
        Map an EvaluationOverride to a string representation of the output.
        This gets passed to the LLM judge as an example.
        """
        return None

    def example_expected_output_mapper(self, evaluation_override: EvaluationOverride) -> Optional[str]:
        """
        Map an EvaluationOverride to a string representation of the expected output.
        This gets passed to the LLM judge as an example.
        """
        return None

    def _example_mapper(self, evaluation_override: EvaluationOverride) -> str:
        output = self.example_output_mapper(evaluation_override)
        if output is None:
            raise ValueError(
                f"num_overrides was set to a non-zero value "
                f"but example_output_mapper was not implemented in evaluator {self.id}."
            )
        return dedent(
            f"""
                ------
                Output: {self.example_output_mapper(evaluation_override)}
                Expected Output: {self.example_expected_output_mapper(evaluation_override)}
                Answer: {evaluation_override.override_score.name}
                ------
            """
        ).strip()

    def make_prompt(
        self, test_case: TestCaseType, output: OutputType, recent_overrides: List[EvaluationOverride]
    ) -> str:
        """
        Builds a prompt like:
        Is the output accurate based on the expected output?

        [Output]
        Hey, how are you?

        [Expected Output]
        Hi, how are you doing?

        [Examples]
        ------
        Output: How are you?
        Expected Output: How are you?
        Answer: Accurate
        ------
        """
        base_question = "Is the output accurate based on the expected output?"

        # We only want the unique examples
        override_examples = set([self._example_mapper(override) for override in recent_overrides])
        if len(override_examples) == 0:
            return dedent(
                f"""
                    {base_question}

                    [Output]
                    {self.output_mapper(output=output)}

                    [Expected Output]
                    {self.expected_output_mapper(test_case=test_case)}
                    """
            ).strip()

        joined_examples = "\n".join(override_examples)
        return dedent(
            f"""
                {base_question}

                [Output]
                {self.output_mapper(output=output)}

                [Expected Output]
                {self.expected_output_mapper(test_case=test_case)}

                [Examples]
                {joined_examples}
                """
        ).strip()
