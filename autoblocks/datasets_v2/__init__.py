# Main public re-exports
from .types import (
    Conversation,
    ConversationMessage,
    ConversationTurn,
    DatasetV2,
    DatasetListItemV2,
    DatasetSchemaV2,
    DatasetItemV2,
    DatasetItemsResponseV2,
    CreateDatasetV2Request,
    CreateDatasetItemsV2Request,
    UpdateItemV2Request
)

from .schema import (
    SchemaPropertyType,
    BaseSchemaProperty,
    StringProperty,
    NumberProperty,
    BooleanProperty,
    ListOfStringsProperty,
    SelectProperty,
    MultiSelectProperty,
    ValidJSONProperty,
    ConversationProperty,
    SchemaProperty
)

from .client import DatasetsV2Client, create_datasets_v2_client
from autoblocks._impl.datasets_v2.validation import validate_conversation

__all__ = [
    # Types
    "Conversation",
    "ConversationMessage",
    "ConversationTurn",
    "DatasetV2",
    "DatasetListItemV2", 
    "DatasetSchemaV2",
    "DatasetItemV2",
    "DatasetItemsResponseV2",
    "CreateDatasetV2Request",
    "CreateDatasetItemsV2Request",
    "UpdateItemV2Request",
    
    # Schema
    "SchemaPropertyType",
    "BaseSchemaProperty",
    "StringProperty",
    "NumberProperty",
    "BooleanProperty",
    "ListOfStringsProperty",
    "SelectProperty",
    "MultiSelectProperty",
    "ValidJSONProperty",
    "ConversationProperty",
    "SchemaProperty",
    
    # Client
    "DatasetsV2Client",
    "create_datasets_v2_client",
    
    # Validation
    "validate_conversation"
] 