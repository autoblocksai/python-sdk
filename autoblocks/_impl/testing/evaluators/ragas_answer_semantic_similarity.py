import abc
from typing import Generic

from autoblocks._impl.testing.evaluators.ragas_base import BaseRagas
from autoblocks._impl.testing.models import OutputType
from autoblocks._impl.testing.models import TestCaseType


class BaseRagasAnswerSemanticSimilarity(
    BaseRagas[TestCaseType, OutputType], abc.ABC, Generic[TestCaseType, OutputType]
):
    """
    The RagasAnswerSemanticSimilarity evaluator evaluates the assessment of the semantic resemblance
    between the generated answer and the ground truth.

    See more: https://docs.ragas.io/en/stable/concepts/metrics/semantic_similarity.html
    """

    metric_name = "answer_similarity"
