from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from .schema import SchemaProperty


@dataclass
class ConversationMessage:
    """Conversation message"""
    role: str
    content: str


@dataclass
class ConversationTurn:
    """Conversation turn"""
    turn: int
    messages: List[ConversationMessage]


@dataclass
class Conversation:
    """Conversation"""
    roles: List[str]
    turns: List[ConversationTurn]


@dataclass
class DatasetV2:
    """Dataset V2"""
    id: str
    external_id: str
    name: str
    description: Optional[str]
    created_at: str


@dataclass
class DatasetListItemV2:
    """Dataset list item"""
    id: str
    external_id: str
    name: str
    description: Optional[str]
    latest_revision_id: Optional[str]


@dataclass
class DatasetSchemaV2:
    """Dataset schema"""
    id: str
    external_id: str
    description: Optional[str]
    schema: Optional[List[SchemaProperty]]
    schema_version: int


@dataclass
class DatasetItemV2:
    """Dataset item"""
    id: str
    revision_item_id: Optional[str]
    splits: List[str]
    data: Dict[str, Any]


@dataclass
class DatasetItemsResponseV2:
    """Dataset items response"""
    dataset_id: str
    external_id: str
    revision_id: str
    schema_version: int
    items: List[DatasetItemV2]


@dataclass
class CreateDatasetV2Request:
    """Create dataset request"""
    name: str
    description: Optional[str]
    schema: List[SchemaProperty]


@dataclass
class CreateDatasetItemsV2Request:
    """Create dataset items request"""
    items: List[Dict[str, Any]]
    split_names: Optional[List[str]] = None


@dataclass
class UpdateItemV2Request:
    """Update item request"""
    data: Dict[str, Any]
    split_names: Optional[List[str]] = None 