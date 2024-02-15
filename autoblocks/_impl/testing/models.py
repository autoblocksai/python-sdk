import abc
import dataclasses
import functools
from typing import Any
from typing import Optional


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


@dataclasses.dataclass()
class BaseTestCase(abc.ABC):
    @abc.abstractmethod
    def hash(self) -> str:
        ...

    @functools.cached_property
    def _cached_hash(self) -> str:
        return self.hash()


class BaseEvaluator(abc.ABC):
    @property
    @abc.abstractmethod
    def id(self) -> str:
        ...

    @abc.abstractmethod
    def evaluate(self, test_case: BaseTestCase, output: Any) -> Evaluation:
        ...
