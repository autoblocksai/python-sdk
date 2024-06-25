import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextEntitiesRecall(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextEntities evaluator evaluates the measure of recall of the retrieved context,
    based on the number of entities present in both ground_truths and contexts
    relative to the number of entities present in the ground_truths alone.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_entities_recall.html
    """

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(dataset=dataset, metrics=[ragas.metrics.context_entity_recall])
        return Evaluation(score=result["context_entity_recall"], threshold=self.threshold)
