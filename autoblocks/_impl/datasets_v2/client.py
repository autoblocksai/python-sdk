import requests
from typing import Dict, List, Optional, Union, Any
import dataclasses
import json
from urllib.parse import quote

from .types import (
    DatasetV2, 
    DatasetListItemV2, 
    DatasetSchemaV2, 
    DatasetItemV2,
    DatasetItemsResponseV2,
    CreateDatasetV2Request, 
    CreateDatasetItemsV2Request, 
    UpdateItemV2Request
)


def _encode_uri_component(component: str) -> str:
    """URL encode a URI component"""
    return quote(component, safe='')


# Helper function to convert dataclasses to dict for serialization
def _dataclass_to_dict(obj: Any) -> Any:
    """Convert dataclasses to dictionaries for JSON serialization"""
    if dataclasses.is_dataclass(obj):
        return {k: _dataclass_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    elif isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


class DatasetsV2Client:
    """Datasets V2 API Client"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the client with configuration
        
        Args:
            config: Dict with:
                - api_key: Autoblocks API key
                - app_slug: Application slug
                - timeout_ms: Optional timeout in milliseconds (default: 60000)
        """
        self.api_key = config["api_key"]
        self.app_slug = config["app_slug"]
        self.timeout_sec = config.get("timeout_ms", 60000) / 1000  # Convert to seconds
        self.base_url = "https://api.autoblocks.ai"  # V2 API endpoint
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Autoblocks-SDK": "python-datasets-v2"
        }
    
    def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Any:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        
        # Convert dataclasses to dict if necessary
        if data is not None and any(dataclasses.is_dataclass(v) for v in data.values()):
            data = _dataclass_to_dict(data)
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data if data else None,
            timeout=self.timeout_sec
        )
        
        if not response.ok:
            raise Exception(f"HTTP Request Error: {method} {url} \"{response.status_code} {response.reason}\"")
        
        return response.json()
    
    def list(self) -> List[DatasetListItemV2]:
        """List all datasets in the app"""
        path = f"/apps/{self.app_slug}/datasets"
        response = self._make_request("GET", path)
        return [DatasetListItemV2(**item) for item in response]
    
    def create(self, dataset: CreateDatasetV2Request) -> DatasetV2:
        """Create a new dataset"""
        path = f"/apps/{self.app_slug}/datasets"
        response = self._make_request("POST", path, dataclasses.asdict(dataset))
        return DatasetV2(**response)
    
    def destroy(self, external_id: str) -> Dict[str, bool]:
        """Delete a dataset"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}"
        return self._make_request("DELETE", path)
    
    def get_items(self, external_id: str) -> DatasetItemsResponseV2:
        """Get all items for a dataset"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/items"
        response = self._make_request("GET", path)
        return DatasetItemsResponseV2(**response)
    
    def create_items(self, external_id: str, request: CreateDatasetItemsV2Request) -> Dict[str, Any]:
        """Add items to a dataset"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/items"
        return self._make_request("POST", path, dataclasses.asdict(request))
    
    def get_schema_by_version(self, external_id: str, schema_version: int) -> DatasetSchemaV2:
        """Get schema for a specific version"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/schema-versions/{schema_version}"
        response = self._make_request("GET", path)
        return DatasetSchemaV2(**response)
    
    def get_items_by_revision(self, external_id: str, revision_id: str, splits: Optional[List[str]] = None) -> DatasetItemsResponseV2:
        """Get items by revision ID"""
        query_string = f"?splits={','.join(splits)}" if splits else ""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/revisions/{_encode_uri_component(revision_id)}{query_string}"
        response = self._make_request("GET", path)
        return DatasetItemsResponseV2(**response)
    
    def get_items_by_schema_version(self, external_id: str, schema_version: int, splits: Optional[List[str]] = None) -> DatasetItemsResponseV2:
        """Get items by schema version"""
        query_string = f"?splits={','.join(splits)}" if splits else ""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/schema-versions/{schema_version}/items{query_string}"
        response = self._make_request("GET", path)
        return DatasetItemsResponseV2(**response)
    
    def update_item(self, external_id: str, item_id: str, request: UpdateItemV2Request) -> Dict[str, bool]:
        """Update a dataset item"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/items/{_encode_uri_component(item_id)}"
        return self._make_request("PUT", path, dataclasses.asdict(request))
    
    def delete_item(self, external_id: str, item_id: str) -> Dict[str, bool]:
        """Delete a dataset item"""
        path = f"/apps/{self.app_slug}/datasets/{_encode_uri_component(external_id)}/items/{_encode_uri_component(item_id)}"
        return self._make_request("DELETE", path)


def create_datasets_v2_client(config: Dict[str, Any]) -> DatasetsV2Client:
    """
    Create a new datasets v2 client
    
    Args:
        config: Dict with:
            - api_key: Autoblocks API key
            - app_slug: Application slug
            - timeout_ms: Optional timeout in milliseconds (default: 60000)
    
    Returns:
        A DatasetsV2Client instance
    """
    return DatasetsV2Client(config) 