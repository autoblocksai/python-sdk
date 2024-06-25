import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextRecall(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextRecall evaluator evaluates the extent to which the retrieved context
    aligns with the annotated answer, treated as the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_recall.html
    """

    metric_name = "context_recall"
