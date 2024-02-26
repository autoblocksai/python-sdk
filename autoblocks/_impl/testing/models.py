import abc
import dataclasses
import functools
import uuid
from typing import Any
from typing import Dict
from typing import Optional


@dataclasses.dataclass()
class TracerEvent:
    message: str
    trace_id: str
    timestamp: str
    properties: dict

    @classmethod
    def to_json(cls, event: Dict[str, any]):
        return {
            "message": event.message,
            "traceId": event.trace_id,
            "timestamp": event.timestamp,
            "properties": event.properties,
        }


@dataclasses.dataclass()
class Threshold:
    lt: Optional[float] = None
    lte: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None


@dataclasses.dataclass()
class EventEvaluation:
    evaluator_external_id: str
    score: float
    id: Optional[str] = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Optional[dict] = None
    threshold: Optional[Threshold] = None

    @classmethod
    def to_json(cls, event_evaluation: Dict[str, any]):
        return dict(
            evaluatorExternalId=event_evaluation.evaluator_external_id,
            id=str(event_evaluation.id),
            score=event_evaluation.score,
            metadata=event_evaluation.metadata,
            threshold=dataclasses.asdict(event_evaluation.threshold) if event_evaluation.threshold else None,
        )


# TODO: Rename TestEvaluation?
@dataclasses.dataclass()
class Evaluation:
    score: float
    threshold: Optional[Threshold] = None


class BaseTestCase(abc.ABC):
    @abc.abstractmethod
    def hash(self) -> str:
        pass

    @functools.cached_property
    def _cached_hash(self) -> str:
        return self.hash()


class BaseTestEvaluator(abc.ABC):
    """
    An abstract base class for implementing an evaluator that runs on test cases
    in an offline testing scenario.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @abc.abstractmethod
    def evaluate_test_case(self, test_case: BaseTestCase, output: Any) -> Evaluation:
        pass


class BaseEventEvaluator(abc.ABC):
    """
    An abstract base class for implementing an evaluator that runs on events
    in an online testing scenario.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @abc.abstractmethod
    def evaluate_event(self, event: TracerEvent) -> EventEvaluation:
        pass
