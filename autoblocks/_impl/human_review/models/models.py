"""Human Review API models."""

from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    email: str


class Reviewer(BaseModel):
    """Reviewer model."""

    email: str


class JobListItem(BaseModel):
    """Human Review Job list item."""

    id: str
    name: str
    reviewer: Reviewer


class JobsResponse(BaseModel):
    """Response model for listing jobs."""

    jobs: List[JobListItem]


class BinaryScoreOptions(BaseModel):
    """Binary score options."""

    type: str = "binary"


class DiscreteRangeScoreOptions(BaseModel):
    """Discrete range score options."""

    type: str = "discreteRange"
    min: int
    max: int
    description: Optional[Dict[str, str]] = None


class TagScoreOptions(BaseModel):
    """Tag score options."""

    type: str = "tag"


ScoreOptions = Union[BinaryScoreOptions, DiscreteRangeScoreOptions, TagScoreOptions]


class Score(BaseModel):
    """Score model."""

    id: str
    name: str
    description: str
    options: ScoreOptions


class JobItem(BaseModel):
    """Job item reference."""

    id: str


class Job(BaseModel):
    """Human Review Job details."""

    id: str
    name: str
    reviewer: Reviewer
    scores: List[Score]
    items: List[JobItem]


class Grade(BaseModel):
    """Grade model."""

    scoreId: str
    grade: float
    user: User


class ContentType(str, Enum):
    """Content type for fields."""

    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    LINK = "LINK"


class Field(BaseModel):
    """Field model for input/output fields."""

    id: str
    name: str
    value: str
    contentType: ContentType


class FieldComment(BaseModel):
    """Field comment model."""

    fieldId: str
    value: str
    startIdx: Optional[int] = None
    endIdx: Optional[int] = None
    inRelationToScoreName: Optional[str] = None
    user: User


class Comment(BaseModel):
    """Comment model for input/output comments."""

    value: str
    inRelationToScoreName: Optional[str] = None
    user: User


class JobItemDetail(BaseModel):
    """Job item details."""

    id: str
    grades: List[Grade]
    inputFields: List[Field]
    outputFields: List[Field]
    fieldComments: List[FieldComment]
    inputComments: List[Comment]
    outputComments: List[Comment]


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
