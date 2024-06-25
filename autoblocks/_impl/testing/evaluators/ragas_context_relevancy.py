import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextRelevancy(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextRelevancy evaluator evaluates the relevancy of the retrieved context,
    calculated based on both the question and contexts

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_relevancy.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.context_relevancy])
        return Evaluation(score=result["context_relevancy"], threshold=self.threshold)
