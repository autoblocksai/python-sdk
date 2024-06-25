import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasAnswerRelevancy(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasAnswerRelevancy evaluator focuses on assessing how pertinent the generated answer is to the given prompt.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/answer_relevance.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.answer_relevancy])
        return Evaluation(score=result["answer_relevancy"], threshold=self.threshold)