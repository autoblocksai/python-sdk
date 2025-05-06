"""Dataset models for Datasets V2 API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
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
    name: str
    description: Optional[str] = Field(default=None)
    created_at: str = Field(alias="createdAt")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class DatasetListItemV2(BaseModel):
    """Dataset list item"""

    id: str
    external_id: str = Field(alias="externalId")
    name: str
    description: Optional[str] = Field(default=None)
    latest_revision_id: Optional[str] = Field(None, alias="latestRevisionId")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class DatasetSchemaV2(BaseModel):
    """Dataset schema"""

    id: str
    external_id: str = Field(alias="externalId")
    description: Optional[str] = Field(default=None)
    schema_version: int = Field(alias="schemaVersion")
    _schema_props: Optional[List[SchemaPropertyUnion]] = Field(default=None, exclude=True, alias="schema")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }

    @property
    def schema_props(self) -> Optional[List[SchemaPropertyUnion]]:
        """Get schema properties"""
        return self._schema_props

    @schema_props.setter
    def schema_props(self, value: Optional[List[SchemaPropertyUnion]]) -> None:
        """Set schema properties"""
        self._schema_props = value

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

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class DatasetItemsResponseV2(BaseModel):
    """Dataset items response"""

    dataset_id: str
    external_id: str
    revision_id: str
    schema_version: int
    items: List[DatasetItemV2]

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class DatasetItemsSuccessResponse(BaseModel):
    """Dataset items success response"""

    count: int
    revision_id: str = Field(alias="revisionId")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class SuccessResponse(BaseModel):
    """Generic success response"""

    success: bool

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class CreateDatasetV2Request(BaseModel):
    """Create dataset request"""

    name: str
    description: Optional[str] = Field(default=None)
    _schema_props: List[SchemaPropertyUnion] = Field(default_factory=empty_list_factory, exclude=True, alias="schema")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }

    @property
    def schema_props(self) -> List[SchemaPropertyUnion]:
        """Get schema properties"""
        return self._schema_props

    @schema_props.setter
    def schema_props(self, value: List[SchemaPropertyUnion]) -> None:
        """Set schema properties"""
        if not value:
            raise ValueError("Schema cannot be empty")
        self._schema_props = value

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Custom dump method to ensure schema properties are included properly"""
        result = super().model_dump(**kwargs)
        # The alias in the Field will handle the serialization to 'schema'
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

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }

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

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }
