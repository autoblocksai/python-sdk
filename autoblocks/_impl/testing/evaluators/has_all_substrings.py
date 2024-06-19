from typing import Callable
from typing import Generic
from typing import List

from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class HasAllSubstrings(BaseTestEvaluator, Generic[TestCaseType, OutputType]):
    id = "has-all-substrings"

    def __init__(
        self, output_mapper: Callable[[OutputType], str], test_case_mapper: Callable[[TestCaseType], List[str]]
    ):
        super().__init__()
        self.output_mapper = output_mapper
        self.test_case_mapper = test_case_mapper

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        expected_substrings = self.test_case_mapper(test_case)
        mapped_output = self.output_mapper(output)
        missing_substrings = [s for s in expected_substrings if s not in mapped_output]
        score = 0 if missing_substrings else 1
        return Evaluation(score=score, threshold=Threshold(gte=1), metadata={"missing_substrings": missing_substrings})
