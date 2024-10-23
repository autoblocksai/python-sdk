import abc
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl.testing.evaluators.util import get_ragas
from autoblocks._impl.testing.evaluators.util import round_and_clamp_score
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseRagasNonLLMContextRecall(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasNonLLMContextRecall evaluator uses non llm string comparison metrics
    to identify if a retrieved context is relevant or not.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall
    """

    @property
    def threshold(self) -> Optional[Threshold]:
        return None

    @abc.abstractmethod
    def reference_contexts_mapper(self, test_case: TestCaseType) -> List[str]:
        """
        Map your test case to the reference contexts passed to Ragas
        """
        pass

    @abc.abstractmethod
    def retrieved_contexts_mapper(self, test_case: TestCaseType, output: OutputType) -> List[str]:
        """
        Map your test case and output to the retrieved contexts passed to Ragas
        """
        pass

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        ragas = get_ragas(evaluator_id=self.id)
        sample = ragas.SingleTurnSample(
            reference_contexts=self.reference_contexts_mapper(test_case=test_case),
            retrieved_contexts=self.retrieved_contexts_mapper(test_case=test_case, output=output),
        )

        # Instantiate the metric with appropriate arguments
        scorer = ragas.metrics.NonLLMContextRecall()
        result = await scorer.single_turn_ascore(sample=sample)
        return Evaluation(score=round_and_clamp_score(score=result), threshold=self.threshold)
