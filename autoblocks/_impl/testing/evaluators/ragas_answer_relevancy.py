import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasAnswerRelevancy(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasAnswerRelevancy evaluator focuses on assessing how pertinent the generated answer is to the given prompt.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/answer_relevance.html
    """

    metric_name = "answer_relevancy"
