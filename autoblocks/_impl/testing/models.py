import abc
import dataclasses
import functools
from typing import Any
from typing import Awaitable
from typing import Dict
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import Union


@dataclasses.dataclass
class TracerEvent:
    message: str
    timestamp: str
    properties: Dict[str, Any]
    trace_id: Optional[str]


@dataclasses.dataclass
class Threshold:
    lt: Optional[float] = None
    lte: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None


@dataclasses.dataclass
class Evaluation:
    score: float
    threshold: Optional[Threshold] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclasses.dataclass
class TestCaseConfig:
    __test__ = False  # See https://docs.pytest.org/en/7.1.x/example/pythoncollection.html#customizing-test-collection
    repeat_num_times: Optional[int] = None


@dataclasses.dataclass
class HumanReviewField:
    name: str
    value: str

    def serialize(self) -> Dict[str, str]:
        return dict(
            name=self.name,
            value=self.value,
        )


class BaseTestCase(abc.ABC):
    @abc.abstractmethod
    def hash(self) -> str:
        """
        This hash is used to identify this test case throughout its lifetime.
        """
        pass

    def serialize(self) -> Any:
        """
        Override this method to customize how the test case is serialized before being sent to Autoblocks.
        """
        return self

    def serialize_for_human_review(self) -> Optional[list[HumanReviewField]]:
        """
        Can be overridden to customize how the test case is displayed in Autoblocks Human Review,
        e.g. to add, remove, or transform fields.
        """
        return None


TestCaseType = TypeVar("TestCaseType", bound=BaseTestCase)
OutputType = TypeVar("OutputType")


@dataclasses.dataclass
class TestCaseContext(Generic[TestCaseType]):
    """
    This class serves as a container for the user's test case +
    utilities around that test case.
    """

    # The user's test case
    test_case: TestCaseType

    # Defined if the user has configured their test case to repeat
    repetition_idx: Optional[int]

    @functools.cached_property
    def _cached_hash(self) -> str:
        return self.test_case.hash()

    def hash(self) -> str:
        if self.repetition_idx is not None:
            # In the future, instead of modifying the hash, we should
            # leave the hash as-is and instead pass the repetition idx
            # in the /results request and make it a top level attribute
            # in our data model.
            return f"{self._cached_hash}-{self.repetition_idx}"
        return self._cached_hash


class BaseTestEvaluator(abc.ABC):
    """
    An ABC for users that are implementing an evaluator that will only be run against test cases.
    """

    # Controls how many concurrent evaluations can be run for this evaluator
    max_concurrency = 10

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not isinstance(cls.max_concurrency, int):
            raise TypeError(f"{cls.__name__}.max_concurrency must be an int")

    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @abc.abstractmethod
    def evaluate_test_case(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Union[Optional[Evaluation], Awaitable[Optional[Evaluation]]]:
        pass


class BaseEventEvaluator(abc.ABC):
    """
    An ABC for users that are implementing an evaluator that will only be run against production events.
    """

    # Controls how many concurrent evaluations can be run for this evaluator
    max_concurrency = 10

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not isinstance(cls.max_concurrency, int):
            raise TypeError(f"{cls.__name__}.max_concurrency must be an int")

    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @abc.abstractmethod
    def evaluate_event(self, event: TracerEvent) -> Union[Optional[Evaluation], Awaitable[Optional[Evaluation]]]:
        pass


class BaseEvaluator(
    BaseTestEvaluator,
    BaseEventEvaluator,
    abc.ABC,
):
    """
    An ABC for users that are implementing an evaluator that will be run against both test cases and production events.
    """


@dataclasses.dataclass
class ScoreChoice:
    """
    A choice used in an LLM judge evaluator.
    """

    value: float
    name: str


@dataclasses.dataclass
class EvaluationOverrideField:
    id: str
    name: str
    value: str


@dataclasses.dataclass
class EvaluationOverrideComment:
    field_id: str
    quoted_text: str
    comment_text: str


@dataclasses.dataclass
class EvaluationOverride:
    """
    An override for an evaluator. Used to give examples to an LLM judge.
    """

    original_score: ScoreChoice
    override_score: ScoreChoice
    input_fields: list[EvaluationOverrideField]
    output_fields: list[EvaluationOverrideField]
    comments: list[EvaluationOverrideComment]
