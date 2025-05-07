"""Schema models for Datasets API."""

from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Type
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator


class SchemaPropertyType(str, Enum):
    """Schema property types enum"""

    STRING = "String"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    LIST_OF_STRINGS = "List of Strings"
    SELECT = "Select"
    MULTI_SELECT = "Multi-Select"
    VALID_JSON = "Valid JSON"
    CONVERSATION = "Conversation"


class BaseSchemaProperty(BaseModel):
    """Base property interface"""

    id: str
    name: str
    required: bool

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate id is non-empty"""
        if not v.strip():
            raise ValueError("ID cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty"""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v


class StringProperty(BaseSchemaProperty):
    """String property"""

    type: Literal[SchemaPropertyType.STRING]


class NumberProperty(BaseSchemaProperty):
    """Number property"""

    type: Literal[SchemaPropertyType.NUMBER]


class BooleanProperty(BaseSchemaProperty):
    """Boolean property"""

    type: Literal[SchemaPropertyType.BOOLEAN]


class ListOfStringsProperty(BaseSchemaProperty):
    """List of strings property"""

    type: Literal[SchemaPropertyType.LIST_OF_STRINGS]


# Shared options validation method
def validate_options(class_name: str, v: List[str]) -> List[str]:
    """Validate that options is not empty"""
    if not v:
        raise ValueError(f"Options cannot be empty for {class_name}")
    return v


class SelectProperty(BaseSchemaProperty):
    """Select property"""

    type: Literal[SchemaPropertyType.SELECT]
    options: List[str]

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[str]) -> List[str]:
        """Validate that options is not empty"""
        return validate_options("SelectProperty", v)


class MultiSelectProperty(BaseSchemaProperty):
    """Multi-select property"""

    type: Literal[SchemaPropertyType.MULTI_SELECT]
    options: List[str]

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[str]) -> List[str]:
        """Validate that options is not empty"""
        return validate_options("MultiSelectProperty", v)


class ValidJSONProperty(BaseSchemaProperty):
    """Valid JSON property"""

    type: Literal[SchemaPropertyType.VALID_JSON]


class ConversationProperty(BaseSchemaProperty):
    """Conversation property"""

    type: Literal[SchemaPropertyType.CONVERSATION]
    roles: Optional[List[str]] = None


# Schema property union type using discriminated unions
SchemaProperty = Union[
    StringProperty,
    NumberProperty,
    BooleanProperty,
    ListOfStringsProperty,
    SelectProperty,
    MultiSelectProperty,
    ValidJSONProperty,
    ConversationProperty,
]


# Type mapping for factory function
PROPERTY_TYPE_MAP: Dict[
    SchemaPropertyType,
    Type[SchemaProperty],
] = {
    SchemaPropertyType.STRING: StringProperty,
    SchemaPropertyType.NUMBER: NumberProperty,
    SchemaPropertyType.BOOLEAN: BooleanProperty,
    SchemaPropertyType.LIST_OF_STRINGS: ListOfStringsProperty,
    SchemaPropertyType.SELECT: SelectProperty,
    SchemaPropertyType.MULTI_SELECT: MultiSelectProperty,
    SchemaPropertyType.VALID_JSON: ValidJSONProperty,
    SchemaPropertyType.CONVERSATION: ConversationProperty,
}


def create_schema_property(data: Dict[str, Any]) -> SchemaProperty:
    """
    Factory function to create the right type of schema property based on the type field.

    Args:
        data: Dictionary with the property data

    Returns:
        The appropriate SchemaProperty subclass instance

    Raises:
        ValueError: If the type is unknown or the property is invalid
    """
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")

    if "type" not in data:
        raise ValueError("Schema property must have a 'type' field")

    prop_type = data["type"]

    # Try to get the property type as an enum
    try:
        if isinstance(prop_type, str):
            prop_type = SchemaPropertyType(prop_type)
    except ValueError:
        raise ValueError(f"Unknown schema property type: {prop_type}")

    # Get the model class based on the type
    model_class = PROPERTY_TYPE_MAP.get(prop_type)

    if not model_class:
        raise ValueError(f"Unknown schema property type: {prop_type}")

    # Validate and create the model
    property_instance = model_class.model_validate(data)
    return property_instance
