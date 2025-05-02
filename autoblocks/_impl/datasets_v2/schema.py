from enum import Enum
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass


class SchemaPropertyType(str, Enum):
    """Schema property types enum"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST_OF_STRINGS = "list_of_strings"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    VALID_JSON = "valid_json"
    CONVERSATION = "conversation"


@dataclass
class BaseSchemaProperty:
    """Base property interface"""
    id: str
    name: str
    required: bool
    type: SchemaPropertyType


@dataclass
class StringProperty(BaseSchemaProperty):
    """String property"""
    type: SchemaPropertyType = SchemaPropertyType.STRING


@dataclass
class NumberProperty(BaseSchemaProperty):
    """Number property"""
    type: SchemaPropertyType = SchemaPropertyType.NUMBER


@dataclass
class BooleanProperty(BaseSchemaProperty):
    """Boolean property"""
    type: SchemaPropertyType = SchemaPropertyType.BOOLEAN


@dataclass
class ListOfStringsProperty(BaseSchemaProperty):
    """List of strings property"""
    type: SchemaPropertyType = SchemaPropertyType.LIST_OF_STRINGS


@dataclass
class SelectProperty(BaseSchemaProperty):
    """Select property"""
    options: List[str]
    type: SchemaPropertyType = SchemaPropertyType.SELECT


@dataclass
class MultiSelectProperty(BaseSchemaProperty):
    """Multi-select property"""
    options: List[str]
    type: SchemaPropertyType = SchemaPropertyType.MULTI_SELECT


@dataclass
class ValidJSONProperty(BaseSchemaProperty):
    """Valid JSON property"""
    type: SchemaPropertyType = SchemaPropertyType.VALID_JSON


@dataclass
class ConversationProperty(BaseSchemaProperty):
    """Conversation property"""
    roles: Optional[List[str]] = None
    type: SchemaPropertyType = SchemaPropertyType.CONVERSATION


# Schema property union type
SchemaProperty = Union[
    StringProperty,
    NumberProperty,
    BooleanProperty,
    ListOfStringsProperty,
    SelectProperty,
    MultiSelectProperty,
    ValidJSONProperty,
    ConversationProperty
] 