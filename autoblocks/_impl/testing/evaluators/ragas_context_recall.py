import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import RagasBase
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class RagasContextRecall(RagasBase[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextRecall evaluator evaluates the extent to which the retrieved context
    aligns with the annotated answer, treated as the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_recall.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.context_recall])
        return Evaluation(score=result["context_recall"], threshold=self.threshold)
