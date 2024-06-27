import abc
import json
from typing import Generic

from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseIsValidJSON(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The IsValidJSON evaluator checks if the output is valid JSON.
    Scores 1 if it is valid, 0 otherwise.
    """

    @abc.abstractmethod
    def output_mapper(self, output: OutputType) -> str:
        """
        Map your output to the string that you want to check is valid JSON.
        """
        pass

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        mapped_output = self.output_mapper(output)
        score = 1
        metadata = None
        try:
            json.loads(mapped_output)
        except Exception as e:
            score = 0
            metadata = {"error": str(e)}
        return Evaluation(score=score, threshold=Threshold(gte=1), metadata=metadata)
