import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import RagasBase
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class RagasContextPrecision(RagasBase[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextPrecision evaluator evaluates
    whether all of the ground-truth relevant items present in the contexts are ranked higher or not.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_precision.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.context_precision])
        return Evaluation(score=result["context_precision"], threshold=self.threshold)
