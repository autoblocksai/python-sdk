import abc
from typing import Any
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


class BaseRagasNoiseSensitivity(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasNoiseSensitivity evaluator measures how often a system makes errors by providing incorrect responses when
    utilizing either relevant or irrelevant retrieved documents.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity
    """

    @property
    def threshold(self) -> Optional[Threshold]:
        return None

    @property
    def focus(self) -> Optional[str]:
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
    def user_input_mapper(self, test_case: TestCaseType, output: OutputType) -> str:
        """
        Map your test case or output to the user input passed to Ragas
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

    @abc.abstractmethod
    def retrieved_contexts_mapper(self, test_case: TestCaseType, output: OutputType) -> List[str]:
        """
        Map your test case and output to the retrieved contexts passed to Ragas
        """
        pass

    async def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        ragas = get_ragas(evaluator_id=self.id)
        sample = ragas.SingleTurnSample(
            user_input=self.user_input_mapper(test_case=test_case, output=output),
            response=self.response_mapper(output=output),
            reference=self.reference_mapper(test_case=test_case),
            retrieved_contexts=self.retrieved_contexts_mapper(test_case=test_case, output=output),
        )

        # Instantiate the metric with appropriate arguments
        scorer = (
            ragas.metrics.NoiseSensitivity(llm=self.llm, focus=self.focus)
            if self.focus is not None
            else ragas.metrics.NoiseSensitivity(llm=self.llm)
        )
        result = await scorer.single_turn_ascore(sample=sample)
        return Evaluation(score=round_and_clamp_score(score=result), threshold=self.threshold)
