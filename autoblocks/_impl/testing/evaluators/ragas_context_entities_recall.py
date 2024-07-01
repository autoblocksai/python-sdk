import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasContextEntitiesRecall(BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]):
    """
    The RagasContextEntities evaluator evaluates the measure of recall of the retrieved context,
    based on the number of entities present in both ground_truths and contexts
    relative to the number of entities present in the ground_truths alone.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/context_entities_recall.html
    """

    metric_name = "context_entity_recall"
