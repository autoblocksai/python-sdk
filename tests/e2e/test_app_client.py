import os
from typing import Generator

import pytest

from autoblocks.api.app_client import AutoblocksAppClient
from tests.e2e.datasets_v2.setup import create_unique_name
from tests.e2e.datasets_v2.setup import get_basic_schema

pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api-v2.autoblocks.ai"])

# Constants for testing
APP_SLUG = "ci-app"


def create_app_client() -> AutoblocksAppClient:
    """Create an app client for testing with real API calls."""
    api_key = os.environ.get("AUTOBLOCKS_V2_API_KEY")
    if not api_key:
        raise ValueError("AUTOBLOCKS_V2_API_KEY environment variable is required for tests")

    return AutoblocksAppClient(
        api_key=api_key,
        app_slug=APP_SLUG,
    )


class TestAutoblocksAppClient:
    """Test the AutoblocksAppClient."""

    @pytest.fixture(scope="class")
    def client(self) -> AutoblocksAppClient:
        return create_app_client()

    @pytest.fixture(scope="class")
    def test_dataset_id(self, client: AutoblocksAppClient) -> Generator[str, None, None]:
        """Create a test dataset for testing and return its ID."""
        dataset = client.datasets.create(name=create_unique_name("App Client Dataset"), schema=get_basic_schema())
        dataset_id = dataset.external_id

        # Yield the dataset ID for tests to use
        yield dataset_id

        # Clean up
        client.datasets.destroy(dataset_id_kwarg=dataset_id)

    def test_create_and_list_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test creating and listing datasets using the app client."""
        # List all datasets
        datasets = client.datasets.list()

        # Verify our test dataset is in the list
        assert len(datasets) > 0
        test_dataset = next((d for d in datasets if d.external_id == test_dataset_id), None)
        assert test_dataset is not None

    def test_dataset_crud_operations(self, client: AutoblocksAppClient) -> None:
        """Test complete CRUD operations on datasets using the app client."""
        # Create a dataset
        dataset_name = create_unique_name("App Client CRUD Test")
        dataset = client.datasets.create(name=dataset_name, schema=get_basic_schema())
        assert dataset.external_id is not None

        # Create items
        items = [
            {
                "Text Field": "Sample text",
                "Number Field": 42,
            }
        ]
        create_result = client.datasets.create_items(
            items_kwarg=items, dataset_id_kwarg=dataset.external_id, split_names=["train"]
        )
        assert create_result.count == 1

        # Get items
        retrieved_items = client.datasets.get_items(dataset_id_kwarg=dataset.external_id)
        assert len(retrieved_items) == 1
        assert retrieved_items[0].data["Text Field"] == "Sample text"

        # Update item
        update_data = {
            "Text Field": "Updated text",
            "Number Field": 100,
        }
        update_result = client.datasets.update_item(
            dataset_id_kwarg=dataset.external_id,
            item_id_kwarg=retrieved_items[0].id,
            data_kwarg=update_data,
        )
        assert update_result.success is True

        # Verify update
        updated_items = client.datasets.get_items(dataset_id_kwarg=dataset.external_id)
        assert len(updated_items) == 1
        assert updated_items[0].data["Text Field"] == "Updated text"

        # Delete item
        delete_result = client.datasets.delete_item(
            dataset_id_kwarg=dataset.external_id, item_id_kwarg=retrieved_items[0].id
        )
        assert delete_result.success is True

        # Verify deletion
        empty_items = client.datasets.get_items(dataset_id_kwarg=dataset.external_id)
        assert len(empty_items) == 0

        # Delete dataset
        delete_dataset_result = client.datasets.destroy(dataset_id_kwarg=dataset.external_id)
        assert delete_dataset_result.success is True

        # Verify dataset deletion
        all_datasets = client.datasets.list()
        deleted_dataset = next((d for d in all_datasets if d.external_id == dataset.external_id), None)
        assert deleted_dataset is None
