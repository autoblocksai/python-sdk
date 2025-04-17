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
    LINK = "link"
    MARKDOWN = "markdown"
    HTML = "html"


class HumanReviewJobTestCaseStatus(StrEnum):
    SUBMITTED = "Submitted"
    PENDING = "Pending"
    DRAFT = "Draft"


@dataclass
class HumanReviewReviewer:
    id: str
    email: str


@dataclass
class HumanReviewJob:
    id: str
    name: str
    reviewer: HumanReviewReviewer


@dataclass
class HumanReviewJobTestCase:
    id: str
    status: HumanReviewJobTestCaseStatus


@dataclass
class HumanReviewJobWithTestCases(HumanReviewJob):
    test_cases: List[HumanReviewJobTestCase]


@dataclass
class HumanReviewGrade:
    name: str
    grade: float


@dataclass
class HumanReviewAutomatedEvaluation:
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
class HumanReviewFieldComment:
    field_id: str
    value: str
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    in_relation_to_grade_name: Optional[str] = None
    in_relation_to_automated_evaluation_id: Optional[str] = None


@dataclass
class HumanReviewGeneralComment:
    value: str
    in_relation_to_grade_name: Optional[str] = None
    in_relation_to_automated_evaluation_id: Optional[str] = None


@dataclass
class HumanReviewJobTestCaseResult:
    id: str
    reviewer: HumanReviewReviewer
    status: HumanReviewJobTestCaseStatus
    grades: List[HumanReviewGrade]
    automated_evaluations: List[HumanReviewAutomatedEvaluation]
    input_fields: List[HumanReviewField]
    output_fields: List[HumanReviewField]
    field_comments: List[HumanReviewFieldComment]
    input_comments: List[HumanReviewGeneralComment]
    output_comments: List[HumanReviewGeneralComment]


@dataclass
class DatasetItem:
    id: str
    revision_id: str
    splits: List[str]
    data: Dict[str, Any]


@dataclass
class Dataset:
    name: str
    schema_version: str
    revision_id: str
    items: List[DatasetItem]


@dataclass
class AutoblocksTestRun:
    id: str


@dataclass
class AutoblocksTestCaseResultId:
    id: str


@dataclass
class EvaluationAssertion:
    passed: bool
    required: bool
    criterion: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationWithEvaluatorId:
    evaluator_id: str
    score: float
    passed: Optional[bool]
    metadata: Optional[Dict[str, Any]]
    assertions: List[EvaluationAssertion]
    threshold: Optional[Dict[str, Optional[float]]] = None


@dataclass
class AutoblocksTestCaseResult:
    id: str
    run_id: str
    hash: str
    dataset_item_id: Optional[str]
    duration_ms: Optional[int]
    events: List[Event]
    body: Any
    output: Any


@dataclass
class AutoblocksTestCaseResultWithEvaluations(AutoblocksTestCaseResult):
    evaluations: List[EvaluationWithEvaluatorId]


@dataclass
class AutoblocksTestCaseResultPairId:
    id: str


@dataclass
class AutoblocksTestCaseResultInPair:
    id: str
    input_fields: List[HumanReviewField]
    output_fields: List[HumanReviewField]
    field_comments: List[HumanReviewFieldComment]
    input_comments: List[HumanReviewGeneralComment]
    output_comments: List[HumanReviewGeneralComment]


@dataclass
class AutoblocksTestCaseResultPair:
    pair_id: str
    chosen_id: Optional[str]
    test_cases: List[AutoblocksTestCaseResultInPair]
