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

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.testing.evaluators.util import get_autoblocks_api_key
from autoblocks._impl.testing.evaluators.util import get_test_id


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


@dataclasses.dataclass
class HumanReviewFieldOverride:
    id: str
    name: str
    value: str


@dataclasses.dataclass
class HumanReviewComment:
    field_id: str
    quoted_text: str
    comment_text: str


@dataclasses.dataclass
class EvaluatorOverride:
    original_score: float
    override_score: float
    output_fields: list[HumanReviewFieldOverride]
    comments: list[HumanReviewComment]


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

    async def get_recent_overrides(self) -> Optional[EvaluatorOverride]:
        test_id = get_test_id(evaluator_id=self.id)
        resp = await global_state.http_client().get(
            f"{API_ENDPOINT}/test-suites/{test_id}/human-reviews",
            headers={"Authorization": f"Bearer {get_autoblocks_api_key(self.id)}"},
        )
        resp.raise_for_status()
        # convert to EvaluatorOverride by checking self.id for the name in automatedEvals
        data = resp.json()[0]
        output_fields = [HumanReviewFieldOverride(**field) for field in data["outputFields"]]

        for eval_data in data["automatedEvals"]:
            if eval_data["name"] == self.id:
                return EvaluatorOverride(
                    original_score=eval_data["grades"][0]["originalGrade"],
                    override_score=eval_data["grades"][0]["overrideGrade"],
                    output_fields=output_fields,
                    comments=[
                        HumanReviewComment(
                            field_id=comment["fieldId"],
                            quoted_text=comment["quotedText"],
                            comment_text=comment["commentText"],
                        )
                        for comment in eval_data["comments"]
                    ],
                )

        return None


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
    A choice used in an LLMJudge evaluation.
    """

    value: float
    name: str
