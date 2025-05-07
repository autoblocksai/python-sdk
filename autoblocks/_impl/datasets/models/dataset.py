"""Dataset models for Datasets API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from autoblocks._impl.datasets.models.schema import SchemaProperty
from autoblocks._impl.util import cuid_generator

# Type alias for schema property lists
SchemaPropertyList = List[Union[SchemaProperty, Dict[str, Any]]]


class Dataset(BaseModel):
    """Dataset V2"""

    id: str
    external_id: str = Field(alias="externalId")
    name: Optional[str] = None
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    latest_revision_id: Optional[str] = Field(default=None, alias="latestRevisionId")
    schema_version: Optional[int] = Field(default=None, alias="schemaVersion")
    schema_properties: Optional[List[SchemaProperty]] = Field(default=None, alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class DatasetListItem(BaseModel):
    """Dataset list item V2"""

    id: str
    external_id: str = Field(alias="externalId")
    name: Optional[str] = None
    latest_revision_id: Optional[str] = Field(default=None, alias="latestRevisionId")
    schema_version: Optional[int] = Field(default=None, alias="schemaVersion")
    schema_properties: Optional[List[SchemaProperty]] = Field(default=None, alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class DatasetSchema(BaseModel):
    """Dataset schema V2"""

    id: str
    external_id: str = Field(alias="externalId")
    schema_properties: Optional[List[SchemaProperty]] = Field(default=None, alias="schema")
    schema_version: int = Field(alias="schemaVersion")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class DatasetItem(BaseModel):
    """Dataset item V2"""

    id: str
    revision_item_id: Optional[str] = Field(default=None, alias="revisionItemId")
    splits: List[str] = []
    data: Dict[str, Any]

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class CreateDatasetRequest(BaseModel):
    """Request to create a dataset V2"""

    name: str
    schema_properties: SchemaPropertyList = Field(alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty"""
        if not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_schema(self) -> "CreateDatasetRequest":
        """Ensure schema properties have IDs"""
        if self.schema_properties:
            for i, prop in enumerate(self.schema_properties):
                # If it's a dict, ensure it has an id
                if isinstance(prop, dict) and "id" not in prop:
                    prop["id"] = cuid_generator()
        return self


class CreateDatasetItemsRequest(BaseModel):
    """Request to create dataset items V2"""

    items: List[Dict[str, Any]]
    split_names: Optional[List[str]] = Field(default=None, alias="splitNames")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate items list is not empty"""
        if not v:
            raise ValueError("Items list cannot be empty")
        return v


class UpdateItemRequest(BaseModel):
    """Request to update a dataset item V2"""

    data: Dict[str, Any]
    split_names: Optional[List[str]] = Field(default=None, alias="splitNames")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class SuccessResponse(BaseModel):
    """Success response"""

    success: bool = True

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class DatasetItemsSuccessResponse(BaseModel):
    """Success response for creating dataset items"""

    count: int
    revision_id: str = Field(alias="revisionId")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )
