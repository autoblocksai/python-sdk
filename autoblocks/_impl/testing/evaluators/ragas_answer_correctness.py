import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasAnswerCorrectness(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasAnswerCorrectness evaluator evaluates the accuracy of the generated answer
    when compared to the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/answer_correctness.html
    """

    metric_name = "answer_correctness"
