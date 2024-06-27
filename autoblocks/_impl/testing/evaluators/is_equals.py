import abc
from typing import Generic

from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseIsEquals(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The IsEquals evaluator checks if the output equals the expected output.
    The comparison is case-sensitive. Scores 1 if it is equal, 0 otherwise.
    """

    @abc.abstractmethod
    def test_case_mapper(self, test_case: TestCaseType) -> str:
        """
        Map your test case to a string for comparison.
        """
        pass

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map your output to a string for comparison.
        """
        pass

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        actual_output = self.output_mapper(output)
        expected_output = self.test_case_mapper(test_case)
        score = 1 if actual_output == expected_output else 0
        metadata = {"expected_output": expected_output, "actual_output": actual_output} if score == 0 else None
        return Evaluation(
            score=score,
            threshold=Threshold(gte=1),
            metadata=metadata,
        )
