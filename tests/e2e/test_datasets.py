from typing import Any
from typing import Dict
from typing import Generator
from typing import List

import pytest

from autoblocks.api.app_client import AutoblocksAppClient
from autoblocks.datasets.models import DatasetItem
from autoblocks.datasets.models import SchemaPropertyType
from tests.e2e.datasets.setup import create_app_client
from tests.e2e.datasets.setup import create_unique_name
from tests.e2e.datasets.setup import get_basic_schema

pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api-v2.autoblocks.ai"])


class TestDatasetBasicCRUDOperations:
    """Test basic CRUD operations on datasets."""

    @pytest.fixture(scope="class")
    def client(self) -> AutoblocksAppClient:
        return create_app_client()

    @pytest.fixture(scope="class")
    def test_dataset_id(self, client: AutoblocksAppClient) -> Generator[str, None, None]:
        """Create a test dataset for testing and return its ID."""
        dataset = client.datasets.create(name=create_unique_name("Basic Dataset"), schema=get_basic_schema())
        dataset_id = dataset.external_id

        # Yield the dataset ID for tests to use
        yield dataset_id

        # Clean up
        client.datasets.destroy(external_id=dataset_id)

    def test_list_datasets_and_include_test_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test listing datasets and finding the test dataset."""
        datasets = client.datasets.list()

        assert len(datasets) > 0
        test_dataset = next((d for d in datasets if d.external_id == test_dataset_id), None)
        assert test_dataset is not None

    def test_create_and_delete_temporary_dataset(self, client: AutoblocksAppClient) -> None:
        """Test creating and deleting a temporary dataset."""
        # Create a dataset using the new keyword-only parameters
        temp_dataset = client.datasets.create(
            name=create_unique_name("Temp Dataset"),
            description="Temporary dataset for deletion test",
            schema=get_basic_schema(),
        )

        assert temp_dataset.external_id is not None

        delete_result = client.datasets.destroy(external_id=temp_dataset.external_id)
        assert delete_result.success is True

        datasets = client.datasets.list()
        deleted_dataset = next((d for d in datasets if d.external_id == temp_dataset.external_id), None)
        assert deleted_dataset is None


class TestConversationSchemaType:
    """Test conversation schema type."""

    @pytest.fixture(scope="class")
    def client(self) -> AutoblocksAppClient:
        return create_app_client()

    @pytest.fixture(scope="class")
    def conversation_dataset_id(self, client: AutoblocksAppClient) -> Generator[str, None, None]:
        """Create a dataset with conversation schema for testing."""
        conversation_schema = [
            {
                "name": "title",
                "type": SchemaPropertyType.STRING.value,
                "required": True,
            },
            {
                "name": "conversation",
                "type": SchemaPropertyType.CONVERSATION.value,
                "required": True,
                "roles": ["user", "assistant"],
            },
        ]

        dataset = client.datasets.create(
            name=create_unique_name("Conversation Dataset"),
            description="Dataset with conversation type for testing",
            schema=conversation_schema,
        )
        dataset_id = dataset.external_id

        # Yield the dataset ID for tests to use
        yield dataset_id

        # Clean up
        client.datasets.destroy(external_id=dataset_id)

    def test_create_and_retrieve_items_with_conversation_data(
        self, client: AutoblocksAppClient, conversation_dataset_id: str
    ) -> None:
        """Test creating and retrieving items with conversation data."""
        conversation_data: Dict[str, Any] = {
            "roles": ["user", "assistant"],
            "turns": [
                {
                    "turn": 1,
                    "messages": [{"role": "user", "content": "Hello, how are you?"}],
                },
                {
                    "turn": 2,
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "I'm doing well, thanks for asking!",
                        },
                    ],
                },
                {
                    "turn": 3,
                    "messages": [
                        {"role": "user", "content": "Can you help me with a question?"},
                    ],
                },
                {
                    "turn": 4,
                    "messages": [
                        {"role": "assistant", "content": "Of course! I'd be happy to help."},
                    ],
                },
            ],
        }

        # Create items with the new keyword-only arguments
        items = [
            {
                "title": "Sample conversation",
                "conversation": conversation_data,
            }
        ]

        create_result = client.datasets.create_items(
            external_id=conversation_dataset_id, items=items, split_names=["train", "test"]
        )

        assert create_result.count == 1

        # Get items with the new keyword-only arguments
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=conversation_dataset_id)

        assert len(retrieved_items) == 1
        assert retrieved_items[0].data["title"] == "Sample conversation"

        # Since conversation is stored as JSON, compare the structure
        assert "conversation" in retrieved_items[0].data

        # Handle the case where conversation might be returned as a JSON string
        retrieved_conversation: Any = retrieved_items[0].data["conversation"]
        if isinstance(retrieved_conversation, str):
            import json

            retrieved_conversation = json.loads(retrieved_conversation)

        # Ensure retrieved_conversation is a dict
        assert isinstance(retrieved_conversation, dict)

        # Compare the values that matter
        assert "roles" in retrieved_conversation
        assert retrieved_conversation["roles"] == conversation_data["roles"]

        # Ensure turns exists and is a list
        assert "turns" in retrieved_conversation
        assert isinstance(retrieved_conversation["turns"], list)

        # Cast to proper type to satisfy type checker
        turns_list: List[Dict[str, Any]] = retrieved_conversation["turns"]
        conversation_turns: List[Dict[str, Any]] = conversation_data["turns"]

        assert len(turns_list) == len(conversation_turns)

        # Use type annotation for turn
        for i, turn_data in enumerate(conversation_turns):
            retrieved_turn = turns_list[i]
            assert isinstance(retrieved_turn, dict)
            assert "turn" in retrieved_turn
            assert retrieved_turn["turn"] == turn_data["turn"]
            assert "messages" in retrieved_turn
            assert isinstance(retrieved_turn["messages"], list)
            assert len(retrieved_turn["messages"]) == len(turn_data["messages"])


class TestDatasetItemsOperations:
    """Test operations on dataset items."""

    # Class variable to store the item ID between test functions
    test_item_id = None

    @pytest.fixture(scope="class")
    def client(self) -> AutoblocksAppClient:
        return create_app_client()

    @pytest.fixture(scope="class")
    def test_dataset_id(self, client: AutoblocksAppClient) -> Generator[str, None, None]:
        """Create a test dataset for testing and return its ID."""
        dataset = client.datasets.create(name=create_unique_name("Items Dataset"), schema=get_basic_schema())
        dataset_id = dataset.external_id

        # Yield the dataset ID for tests to use
        yield dataset_id

        # Clean up
        client.datasets.destroy(external_id=dataset_id)

    def test_add_items_to_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test adding items to the dataset."""
        items = [
            {
                "Text Field": "Sample text 1",
                "Number Field": 42,
            },
            {
                "Text Field": "Sample text 2",
                "Number Field": 43,
            },
        ]

        # Use the new keyword-only arguments
        create_items_result = client.datasets.create_items(
            external_id=test_dataset_id, items=items, split_names=["train", "test"]
        )

        assert create_items_result.count == 2
        assert create_items_result.revision_id is not None

    def test_retrieve_items_from_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test retrieving items from the dataset."""
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id)

        assert len(retrieved_items) == 2

        # Store an item ID for update/delete tests in the class variable
        TestDatasetItemsOperations.test_item_id = retrieved_items[0].id

    def test_update_item_in_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test updating an item in the dataset."""
        # Make sure we have an item ID from the previous test
        assert TestDatasetItemsOperations.test_item_id is not None

        # Use the new keyword-only arguments
        update_data = {
            "Text Field": "Updated sample text",
            "Number Field": 100,
        }

        update_result = client.datasets.update_item(
            external_id=test_dataset_id,
            item_id=TestDatasetItemsOperations.test_item_id,
            data=update_data,
            split_names=["validation"],
        )

        assert update_result.success is True

        # Verify the update
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id)
        updated_item = next(
            (item for item in retrieved_items if item.id == TestDatasetItemsOperations.test_item_id), None
        )

        assert updated_item is not None
        assert updated_item.data["Text Field"] == "Updated sample text"
        assert updated_item.data["Number Field"] == 100
        assert "validation" in updated_item.splits

    def test_delete_item_from_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test deleting an item from the dataset."""
        # Make sure we have an item ID from the previous test
        assert TestDatasetItemsOperations.test_item_id is not None

        # Use the new keyword-only arguments
        delete_result = client.datasets.delete_item(
            external_id=test_dataset_id, item_id=TestDatasetItemsOperations.test_item_id
        )

        assert delete_result.success is True

        # Verify the item is deleted
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id)
        deleted_item = next(
            (item for item in retrieved_items if item.id == TestDatasetItemsOperations.test_item_id), None
        )

        assert deleted_item is None
