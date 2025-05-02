import pytest
from unittest import mock
import json
from autoblocks.datasets_v2 import (
    DatasetsV2Client,
    create_datasets_v2_client,
    CreateDatasetV2Request,
    StringProperty,
    DatasetListItemV2,
    CreateDatasetItemsV2Request
)


def test_create_client():
    """Test creating a client instance"""
    client = create_datasets_v2_client({
        "api_key": "test-api-key",
        "app_slug": "test-app"
    })
    
    assert isinstance(client, DatasetsV2Client)
    assert client.api_key == "test-api-key"
    assert client.app_slug == "test-app"
    assert client.base_url == "https://api.autoblocks.ai"


@mock.patch('requests.request')
def test_list_datasets(mock_request):
    """Test listing datasets"""
    # Setup mock response
    mock_response = mock.Mock()
    mock_response.ok = True
    mock_response.json.return_value = [
        {
            "id": "dataset-id-1",
            "external_id": "test-dataset-1",
            "name": "Test Dataset 1",
            "description": "Description 1",
            "latest_revision_id": "rev-1"
        },
        {
            "id": "dataset-id-2",
            "external_id": "test-dataset-2",
            "name": "Test Dataset 2",
            "description": "Description 2",
            "latest_revision_id": "rev-2"
        }
    ]
    mock_request.return_value = mock_response
    
    # Create client and call the method
    client = create_datasets_v2_client({
        "api_key": "test-api-key",
        "app_slug": "test-app"
    })
    
    datasets = client.list()
    
    # Verify the request was made correctly
    mock_request.assert_called_once_with(
        method="GET",
        url="https://api.autoblocks.ai/apps/test-app/datasets",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer test-api-key",
            "X-Autoblocks-SDK": "python-datasets-v2"
        },
        json=None,
        timeout=60.0
    )
    
    # Verify the response was parsed correctly
    assert len(datasets) == 2
    assert isinstance(datasets[0], DatasetListItemV2)
    assert datasets[0].id == "dataset-id-1"
    assert datasets[0].name == "Test Dataset 1"
    assert datasets[0].latest_revision_id == "rev-1"


@mock.patch('requests.request')
def test_create_dataset(mock_request):
    """Test creating a dataset"""
    # Setup mock response
    mock_response = mock.Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "id": "new-dataset-id",
        "external_id": "customer-chats",
        "name": "Customer Chats",
        "description": "Customer chat dataset",
        "created_at": "2023-01-01T00:00:00Z"
    }
    mock_request.return_value = mock_response
    
    # Create client and prepare the request
    client = create_datasets_v2_client({
        "api_key": "test-api-key",
        "app_slug": "test-app"
    })
    
    request = CreateDatasetV2Request(
        name="Customer Chats",
        description="Customer chat dataset",
        schema=[
            StringProperty(
                id="customer-id",
                name="Customer ID",
                required=True
            )
        ]
    )
    
    # Call the method
    dataset = client.create(request)
    
    # Verify the request data
    called_args = mock_request.call_args
    assert called_args[1]["method"] == "POST"
    assert called_args[1]["url"] == "https://api.autoblocks.ai/apps/test-app/datasets"
    
    # Verify request JSON data 
    json_data = called_args[1]["json"]
    assert json_data["name"] == "Customer Chats"
    assert json_data["description"] == "Customer chat dataset"
    assert len(json_data["schema"]) == 1
    assert json_data["schema"][0]["id"] == "customer-id"
    assert json_data["schema"][0]["name"] == "Customer ID"
    assert json_data["schema"][0]["required"] is True
    assert json_data["schema"][0]["type"] == "string"
    
    # Verify the response parsing
    assert dataset.id == "new-dataset-id"
    assert dataset.name == "Customer Chats"
    assert dataset.external_id == "customer-chats"
    assert dataset.description == "Customer chat dataset"
    assert dataset.created_at == "2023-01-01T00:00:00Z"


@mock.patch('requests.request')
def test_create_items(mock_request):
    """Test creating dataset items"""
    # Setup mock response
    mock_response = mock.Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "success": True,
        "items_added": 2
    }
    mock_request.return_value = mock_response
    
    # Create client and prepare request
    client = create_datasets_v2_client({
        "api_key": "test-api-key",
        "app_slug": "test-app"
    })
    
    request = CreateDatasetItemsV2Request(
        items=[
            {"text": "Item 1", "label": "positive"},
            {"text": "Item 2", "label": "negative"}
        ],
        split_names=["train"]
    )
    
    # Call the method
    result = client.create_items("test-dataset", request)
    
    # Verify the request 
    called_args = mock_request.call_args
    assert called_args[1]["method"] == "POST"
    assert called_args[1]["url"] == "https://api.autoblocks.ai/apps/test-app/datasets/test-dataset/items"
    
    # Verify request JSON
    json_data = called_args[1]["json"]
    assert len(json_data["items"]) == 2
    assert json_data["items"][0]["text"] == "Item 1"
    assert json_data["items"][1]["label"] == "negative"
    assert json_data["split_names"] == ["train"]
    
    # Verify the response
    assert result["success"] is True
    assert result["items_added"] == 2 