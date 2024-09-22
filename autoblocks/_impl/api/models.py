from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl.util import StrEnum


@dataclass
class Event:
    id: str
    trace_id: str
    message: str
    timestamp: str
    properties: Dict[Any, Any]


@dataclass
class Trace:
    id: str
    events: List[Event]


@dataclass
class View:
    id: str
    name: str


@dataclass
class ManagedTestCase:
    id: str
    body: Dict[str, Any]


@dataclass
class ManagedTestCaseResponse:
    test_cases: List[ManagedTestCase]


@dataclass
class TracesResponse:
    next_cursor: Optional[str]
    traces: List[Trace]


@dataclass
class RelativeTimeFilter:
    type: str = "relative"
    seconds: Optional[float] = None
    minutes: Optional[float] = None
    hours: Optional[float] = None
    days: Optional[float] = None
    weeks: Optional[float] = None
    months: Optional[float] = None
    years: Optional[float] = None


@dataclass
class AbsoluteTimeFilter:
    start: str
    end: str
    type: str = "absolute"


class TraceFilterOperator(StrEnum):
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"


class EventFilterOperator(StrEnum):
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUALS = "LESS_THAN_OR_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUALS = "GREATER_THAN_OR_EQUALS"


@dataclass
class EventFilter:
    key: str
    value: str
    operator: EventFilterOperator


@dataclass
class TraceFilter:
    operator: TraceFilterOperator
    event_filters: List[EventFilter]


class SystemEventFilterKey(StrEnum):
    MESSAGE = "SYSTEM:message"
    LABEL = "SYSTEM:label"


class HumanReviewFieldContentType(StrEnum):
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"


@dataclass
class Reviewer:
    id: str
    email: str


@dataclass
class HumanReviewJob:
    id: str
    name: str
    reviewer: Reviewer


@dataclass
class HumanReviewJobTestCase:
    id: str
    status: str  # 'Submitted' or 'Pending'


@dataclass
class HumanReviewJobWithTestCases(HumanReviewJob):
    test_cases: List[HumanReviewJobTestCase]


@dataclass
class Grade:
    name: str
    grade: float


@dataclass
class AutomatedEvaluation:
    id: str
    original_score: float
    override_score: float
    override_reason: Optional[str] = None


@dataclass
class HumanReviewField:
    id: str
    name: str
    value: str
    content_type: HumanReviewFieldContentType


@dataclass
class FieldComment:
    field_id: str
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    value: str = ""
    in_relation_to_grade_name: Optional[str] = None
    in_relation_to_automated_evaluation_id: Optional[str] = None


@dataclass
class GeneralComment:
    value: str
    in_relation_to_grade_name: Optional[str] = None
    in_relation_to_automated_evaluation_id: Optional[str] = None


@dataclass
class HumanReviewJobTestCaseResult:
    id: str
    reviewer: Reviewer
    status: str  # 'Submitted' or 'Pending'
    grades: List[Grade]
    automated_evaluations: List[AutomatedEvaluation]
    input_fields: List[HumanReviewField]
    output_fields: List[HumanReviewField]
    field_comments: List[FieldComment]
    input_comments: List[GeneralComment]
    output_comments: List[GeneralComment]
