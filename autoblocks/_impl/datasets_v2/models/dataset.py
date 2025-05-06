"""Dataset models for Datasets V2 API."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator

from .schema import SchemaProperty


class DatasetV2(BaseModel):
    """Dataset V2"""
    id: str
    external_id: str = Field(alias="externalId")
    name: str
    description: Optional[str] = None
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
    description: Optional[str] = None
    latest_revision_id: Optional[str] = Field(None, alias="latestRevisionId")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class DatasetSchemaV2(BaseModel):
    """Dataset schema"""
    id: str
    external_id: str = Field(alias="externalId")
    description: Optional[str] = None
    schema: Optional[List[SchemaProperty]] = None
    schema_version: int = Field(alias="schemaVersion")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


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


class CreateDatasetV2Request(BaseModel):
    """Create dataset request"""
    name: str
    description: Optional[str] = None
    schema: List[SchemaProperty]

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty"""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v
    
    @field_validator('schema')
    @classmethod
    def validate_schema(cls, v: List[SchemaProperty]) -> List[SchemaProperty]:
        """Validate schema is not empty"""
        if not v:
            raise ValueError("Schema cannot be empty")
        return v


class CreateDatasetItemsV2Request(BaseModel):
    """Create dataset items request"""
    items: List[Dict[str, Any]]
    split_names: Optional[List[str]] = Field(None, alias="splitNames")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }
    
    @field_validator('items')
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