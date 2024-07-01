import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextPrecision(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextPrecision evaluator evaluates
    whether all of the ground-truth relevant items present in the contexts are ranked higher or not.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_precision.html
    """

    metric_name = "context_precision"
