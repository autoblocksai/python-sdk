"""Human Review API models."""

from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class User(BaseModel):
    """User model."""

    email: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Reviewer(BaseModel):
    """Reviewer model."""

    email: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class JobListItem(BaseModel):
    """Human Review Job list item."""

    id: str
    name: str
    reviewer: Reviewer

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class JobsResponse(BaseModel):
    """Response model for listing jobs."""

    jobs: List[JobListItem]

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class BinaryScoreOptions(BaseModel):
    """Binary score options."""

    type: str = Field(default="binary", alias="type")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DiscreteRangeScoreOptions(BaseModel):
    """Discrete range score options."""

    type: str = Field(default="discreteRange", alias="type")
    min: int
    max: int
    description: Optional[Dict[str, str]] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class TagScoreOptions(BaseModel):
    """Tag score options."""

    type: str = Field(default="tag", alias="type")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


ScoreOptions = Union[BinaryScoreOptions, DiscreteRangeScoreOptions, TagScoreOptions]


class Score(BaseModel):
    """Score model."""

    id: str
    name: str
    description: str
    options: ScoreOptions

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class JobItem(BaseModel):
    """Job item reference."""

    id: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Job(BaseModel):
    """Human Review Job details."""

    id: str
    name: str
    reviewer: Reviewer
    scores: List[Score]
    items: List[JobItem]

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Grade(BaseModel):
    """Grade model."""

    score_id: str = Field(alias="scoreId")
    grade: float
    user: User

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ContentType(str, Enum):
    """Content type for fields."""

    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    LINK = "LINK"


class FieldModel(BaseModel):
    """Field model for input/output fields."""

    id: str
    name: str
    value: str
    content_type: ContentType = Field(alias="contentType")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class FieldComment(BaseModel):
    """Field comment model."""

    field_id: str = Field(alias="fieldId")
    value: str
    start_idx: Optional[int] = Field(default=None, alias="startIdx")
    end_idx: Optional[int] = Field(default=None, alias="endIdx")
    in_relation_to_score_name: Optional[str] = Field(default=None, alias="inRelationToScoreName")
    user: User

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Comment(BaseModel):
    """Comment model for input/output comments."""

    value: str
    in_relation_to_score_name: Optional[str] = Field(default=None, alias="inRelationToScoreName")
    user: User

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class JobItemDetail(BaseModel):
    """Job item details."""

    id: str
    grades: List[Grade]
    input_fields: List[FieldModel] = Field(alias="inputFields")
    output_fields: List[FieldModel] = Field(alias="outputFields")
    field_comments: List[FieldComment] = Field(alias="fieldComments")
    input_comments: List[Comment] = Field(alias="inputComments")
    output_comments: List[Comment] = Field(alias="outputComments")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
