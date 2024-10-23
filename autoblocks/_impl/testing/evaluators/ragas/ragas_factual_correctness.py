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


class BaseRagasFactualCorrectness(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasFactualCorrectness evaluator compares and evaluates the factual accuracy of the generated response
    with the reference. This metric is used to determine the extent
    to which the generated response aligns with the reference.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness
    """

    @property
    def threshold(self) -> Optional[Threshold]:
        return None

    @property
    def mode(self) -> Optional[str]:
        return None

    @property
    def atomicity(self) -> Optional[str]:
        return None

    @property
    @abc.abstractmethod
    def llm(self) -> Any:
        """
        Custom LLM for the evaluation

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
        scorer = ragas.metrics.FactualCorrectness(llm=self.llm, mode=self.mode, atomicity=self.atomicity)
        result = await scorer.single_turn_ascore(sample=sample)
        return Evaluation(score=round_and_clamp_score(score=result), threshold=self.threshold)
