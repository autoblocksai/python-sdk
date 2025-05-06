"""Dataset models for Datasets V2 API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from .schema import BooleanProperty
from .schema import ConversationProperty
from .schema import ListOfStringsProperty
from .schema import MultiSelectProperty
from .schema import NumberProperty
from .schema import SelectProperty
from .schema import StringProperty
from .schema import ValidJSONProperty

# Type alias for schema property union
SchemaPropertyUnion = Union[
    StringProperty,
    NumberProperty,
    BooleanProperty,
    ListOfStringsProperty,
    SelectProperty,
    MultiSelectProperty,
    ValidJSONProperty,
    ConversationProperty,
]


# Helper function for creating empty lists with proper typing
def empty_list_factory() -> List[SchemaPropertyUnion]:
    """Return an empty list for default_factory"""
    return []


class DatasetV2(BaseModel):
    """Dataset V2"""

    id: str
    external_id: str = Field(alias="externalId")
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    created_at: Optional[str] = Field(alias="createdAt", default=None)
    latest_revision_id: Optional[str] = Field(None, alias="latestRevisionId")
    data_schema: Optional[List[Dict[str, Any]]] = Field(default=None, alias="schema")
    schema_version: Optional[int] = Field(None, alias="schemaVersion")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",  # Allow extra fields from the API
    )


class DatasetListItemV2(BaseModel):
    """Dataset list item"""

    id: str
    external_id: str = Field(alias="externalId")
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    latest_revision_id: Optional[str] = Field(None, alias="latestRevisionId")
    data_schema: Optional[List[Dict[str, Any]]] = Field(default=None, alias="schema")
    schema_version: Optional[int] = Field(None, alias="schemaVersion")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",  # Allow extra fields from the API
    )


class DatasetSchemaV2(BaseModel):
    """Dataset schema"""

    id: str
    external_id: str = Field(alias="externalId")
    description: Optional[str] = Field(default=None)
    schema_version: int = Field(alias="schemaVersion")
    schema_field: Optional[List[SchemaPropertyUnion]] = Field(default=None, exclude=True, alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @property
    def schema_props(self) -> Optional[List[SchemaPropertyUnion]]:
        """Get schema properties"""
        return self.schema_field

    @schema_props.setter
    def schema_props(self, value: Optional[List[SchemaPropertyUnion]]) -> None:
        """Set schema properties"""
        self.schema_field = value

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Custom dump method to include schema field"""
        result = super().model_dump(**kwargs)
        # The alias in the Field will handle the serialization to 'schema'
        return result


class DatasetItemV2(BaseModel):
    """Dataset item"""

    id: str
    revision_item_id: Optional[str] = Field(None, alias="revisionItemId")
    splits: List[str]
    data: Dict[str, Any]

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class DatasetItemsResponseV2(BaseModel):
    """Dataset items response"""

    dataset_id: str
    external_id: str
    revision_id: str
    schema_version: int
    items: List[DatasetItemV2]

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class DatasetItemsSuccessResponse(BaseModel):
    """Dataset items success response"""

    count: int
    revision_id: str = Field(alias="revisionId")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class SuccessResponse(BaseModel):
    """Generic success response"""

    success: bool

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class CreateDatasetV2Request(BaseModel):
    """Create dataset request"""

    name: str
    description: Optional[str] = Field(default=None)
    schema_field: List[SchemaPropertyUnion] = Field(default_factory=empty_list_factory, exclude=True, alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @property
    def schema_props(self) -> List[SchemaPropertyUnion]:
        """Get schema properties"""
        return self.schema_field

    @schema_props.setter
    def schema_props(self, value: List[SchemaPropertyUnion]) -> None:
        """Set schema properties"""
        if not value:
            raise ValueError("Schema cannot be empty")
        self.schema_field = value

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Custom dump method to ensure schema properties are included properly"""
        # Get the default result but without exclusions for schema_field
        include_excludes = kwargs.pop("exclude", {})
        if "schema_field" in include_excludes:
            include_excludes.pop("schema_field")

        result = super().model_dump(exclude=include_excludes, **kwargs)

        # Explicitly add the schema field with the correct alias
        result["schema"] = [prop.model_dump(by_alias=True, exclude_none=True) for prop in self.schema_field]

        return result

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty"""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v


class CreateDatasetItemsV2Request(BaseModel):
    """Create dataset items request"""

    items: List[Dict[str, Any]]
    split_names: Optional[List[str]] = Field(None, alias="splitNames")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate items is not empty"""
        if not v:
            raise ValueError("Items cannot be empty")
        return v


class UpdateItemV2Request(BaseModel):
    """Update item request"""

    data: Dict[str, Any]
    split_names: Optional[List[str]] = Field(None, alias="splitNames")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )
