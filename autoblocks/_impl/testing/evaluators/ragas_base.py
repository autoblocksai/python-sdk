import abc
from typing import Any
from typing import Generic
from typing import List
from typing import Optional

from autoblocks._impl.testing.evaluators.util import get_openai_client
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.models import Threshold


def round_and_clamp_score(score: float) -> float:
    """
    Ragas returns scores between 0 and 1
    But sometimes returns score like 1.000004 or 0.154313
    We want to round to 2 decimal places for readability.
    and ensure that the score is a max of 1
    """
    return min(round(score, 2), 1)


class BaseRagas(BaseTestEvaluator, abc.ABC, Generic[TestCaseType, OutputType]):
    """
    Base class for Ragas Metrics
    """

    @property
    def llm(self) -> Optional[Any]:
        """
        Custom LLM for the evaluation

        See: https://docs.ragas.io/en/stable/howtos/customisations/bring-your-own-llm-or-embs.html
        """
        return None

    @property
    def embeddings(self) -> Optional[Any]:
        """
        Custom embeddings model for the evaluation

        See: https://docs.ragas.io/en/stable/howtos/customisations/bring-your-own-llm-or-embs.html
        """
        return None

    @property
    @abc.abstractmethod
    def metric_name(self) -> str:
        """
        The ragas metric name
        """
        pass

    @property
    @abc.abstractmethod
    def threshold(self) -> Optional[Threshold]:
        """
        The threshold for the evaluation
        """
        pass

    @abc.abstractmethod
    def question_mapper(self, test_case: TestCaseType, output: OutputType) -> str:
        """
        Map your test case or output to the question passed to Ragas
        """
        pass

    @abc.abstractmethod
    def answer_mapper(self, output: OutputType) -> str:
        """
        Map your output to the answer passed to Ragas
        """
        pass

    @abc.abstractmethod
    def contexts_mapper(self, test_case: TestCaseType, output: OutputType) -> List[str]:
        """
        Map your test case or output to the contexts passed to Ragas
        """
        pass

    @abc.abstractmethod
    def ground_truth_mapper(self, test_case: TestCaseType, output: OutputType) -> str:
        """
        Map your test case or output to the ground truth passed to Ragas
        """
        pass

    def make_dataset(self, test_case: TestCaseType, output: OutputType):  # type: ignore[no-untyped-def]
        try:
            import datasets  # type: ignore[import-untyped]
        except (ImportError, AssertionError):
            raise ImportError(
                f"The {self.id} evaluator requires datasets. You can install it with `pip install datasets`"
            )

        data_dict = {
            "question": [self.question_mapper(test_case, output)],
            "answer": [self.answer_mapper(output)],
            "contexts": [self.contexts_mapper(test_case, output)],
            "ground_truth": [self.ground_truth_mapper(test_case, output)],
        }
        # Convert dictionary to Hugging Face datasets format
        return datasets.Dataset.from_dict(data_dict)

    def get_ragas(self):  # type: ignore[no-untyped-def]
        # We try to get the openai client first, so that if it doesn't exist we can raise a more informative error
        # Ragas throws a more generic error if the client or OpenAI api key is not found
        # We only need to do this if the user isn't using a custom llm and embeddings
        if self.llm is None or self.embeddings is None:
            get_openai_client(evaluator_id=self.id)
        try:
            import ragas  # type: ignore[import-untyped]
        except (ImportError, AssertionError):
            raise ImportError(f"The {self.id} evaluator requires ragas. You can install it with `pip install ragas`")

        return ragas

    def evaluate_test_case(self, test_case: TestCaseType, output: OutputType) -> Evaluation:
        dataset = self.make_dataset(test_case=test_case, output=output)
        ragas = self.get_ragas()  # type: ignore[no-untyped-call]
        result = ragas.evaluate(
            dataset=dataset,
            metrics=[getattr(ragas.metrics, self.metric_name).__class__()],
            llm=self.llm,
            embeddings=self.embeddings,
        )
        return Evaluation(score=round_and_clamp_score(result[self.metric_name]), threshold=self.threshold)
