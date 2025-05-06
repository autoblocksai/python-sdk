"""Data models for Datasets V2 API."""

# Re-export all the models for easy access
from .conversation import (
    Conversation,
    ConversationMessage,
    ConversationTurn
)

from .dataset import (
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
    SchemaProperty,
    StringProperty,
    NumberProperty,
    BooleanProperty,
    ListOfStringsProperty,
    SelectProperty,
    MultiSelectProperty,
    ValidJSONProperty,
    ConversationProperty,
    create_schema_property
)

__all__ = [
    # Conversation models
    'Conversation',
    'ConversationMessage',
    'ConversationTurn',
    
    # Dataset models
    'DatasetV2',
    'DatasetListItemV2',
    'DatasetSchemaV2',
    'DatasetItemV2',
    'DatasetItemsResponseV2',
    'CreateDatasetV2Request',
    'CreateDatasetItemsV2Request',
    'UpdateItemV2Request',
    
    # Schema models
    'SchemaPropertyType',
    'SchemaProperty',
    'StringProperty',
    'NumberProperty',
    'BooleanProperty',
    'ListOfStringsProperty',
    'SelectProperty',
    'MultiSelectProperty',
    'ValidJSONProperty',
    'ConversationProperty',
    'create_schema_property',
] 