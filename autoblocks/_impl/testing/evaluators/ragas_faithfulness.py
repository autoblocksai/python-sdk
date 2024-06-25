import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasFaithfulness(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasFaithfulness evaluator evaluates the factual consistency of the generated answer against the given context.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/faithfulness.html
    """

    metric_name = "faithfulness"
