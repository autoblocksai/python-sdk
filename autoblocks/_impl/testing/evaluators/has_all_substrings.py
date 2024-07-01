import abc
from typing import Generic
from typing import List

from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseHasAllSubstrings(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The HasAllSubstrings evaluator checks if the output contains all the expected substrings.
    Scores 1 if all substrings are present, 0 otherwise.
    The comparison is case-sensitive.
    """

    @abc.abstractmethod
    def test_case_mapper(self, test_case: TestCaseType) -> List[str]:
        """
        Map your test case to a list of strings to check for in the output.
        """
        pass

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map your output to a string for comparison.
        """
        pass

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        expected_substrings = self.test_case_mapper(test_case)
        mapped_output = self.output_mapper(output)
        missing_substrings = [s for s in expected_substrings if s not in mapped_output]
        score = 0 if missing_substrings else 1
        return Evaluation(score=score, threshold=Threshold(gte=1), metadata={"missing_substrings": missing_substrings})
