import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextRelevancy(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextRelevancy evaluator evaluates the relevancy of the retrieved context,
    calculated based on both the question and contexts

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_relevancy.html
    """

    metric_name = "context_relevancy"
