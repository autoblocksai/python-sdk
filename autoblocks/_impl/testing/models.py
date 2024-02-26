import abc
import dataclasses
import functools
from typing import Any
from typing import Dict
from typing import Optional


@dataclasses.dataclass()
class TracerEvent:
    message: str
    trace_id: str
    timestamp: str
    properties: dict

    def to_json(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "traceId": self.trace_id,
            "timestamp": self.timestamp,
            "properties": self.properties,
        }


@dataclasses.dataclass()
class Threshold:
    lt: Optional[float] = None
    lte: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None


@dataclasses.dataclass()
class Evaluation:
    score: float
    threshold: Optional[Threshold] = None
    metadata: Optional[dict] = None


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
    def evaluate_event(self, event: TracerEvent) -> Evaluation:
        pass
