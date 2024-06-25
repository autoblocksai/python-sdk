import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import RagasBase
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class RagasFaithfulness(RagasBase[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasFaithfulness evaluator evaluates the factual consistency of the generated answer against the given context.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/faithfulness.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.faithfulness])
        return Evaluation(score=result["faithfulness"], threshold=self.threshold)
