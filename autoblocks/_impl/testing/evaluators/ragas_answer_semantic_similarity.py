import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasAnswerSemanticSimilarity(
    BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]
):
    """
    The RagasAnswerSemanticSimilarity evaluator evaluates the assessment of the semantic resemblance
    between the generated answer and the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/semantic_similarity.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.answer_similarity])
        return Evaluation(score=result["answer_similarity"], threshold=self.threshold)
