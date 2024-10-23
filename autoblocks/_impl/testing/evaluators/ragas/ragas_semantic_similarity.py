import abc
from typing import Any
from typing import Generic
from typing import Optional

from autoblocks._impl.testing.evaluators.util import get_ragas
from autoblocks._impl.testing.evaluators.util import round_and_clamp_score
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


class BaseRagasSemanticSimilarity(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasSemanticSimilarity evaluator measures the semantic resemblance between the generated answer
    and the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/semantic_similarity
    """

    @property
    def threshold(self) -> Optional[Threshold]:
        return None

    @property
    @abc.abstractmethod
    def embeddings(self) -> Any:
        """
        Custom Embeddings for the evaluation

        See: https://docs.ragas.io/en/stable/howtos/customizations/customize_models
        """
        pass

    @abc.abstractmethod
    def response_mapper(self, output: OutputType) -> str:
        """
        Map your output to the response passed to Ragas
        """
        pass

    @abc.abstractmethod
    def reference_mapper(self, test_case: TestCaseType) -> str:
        """
        Map your test case to the reference passed to Ragas
        """
        pass

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        ragas = get_ragas(evaluator_id=self.id)
        sample = ragas.SingleTurnSample(
            response=self.response_mapper(output=output),
            reference=self.reference_mapper(test_case=test_case),
        )

        # Instantiate the metric with appropriate arguments
        scorer = ragas.metrics.SemanticSimilarity(embeddings=self.embeddings)
        result = await scorer.single_turn_ascore(sample=sample)
        return Evaluation(score=round_and_clamp_score(score=result), threshold=self.threshold)
