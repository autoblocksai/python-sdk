from typing import Any
from typing import Dict
from typing import Generator
from typing import List

import pytest

from autoblocks.api.app_client import AutoblocksAppClient
from autoblocks.datasets.models import Dataset
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
        assert all(isinstance(d, Dataset) for d in datasets)
        test_dataset = next((d for d in datasets if d.external_id == test_dataset_id), None)
        assert test_dataset is not None

    def test_create_and_delete_temporary_dataset(self, client: AutoblocksAppClient) -> None:
        """Test creating and deleting a temporary dataset."""
        # Create a dataset using the new keyword-only parameters
        temp_dataset = client.datasets.create(
            name=create_unique_name("Temp Dataset"),
            schema=get_basic_schema(),
        )

        assert temp_dataset.external_id is not None

        delete_result = client.datasets.destroy(external_id=temp_dataset.external_id)
        assert delete_result.success is True

        datasets = client.datasets.list()
        assert all(isinstance(d, Dataset) for d in datasets)
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

        # Test splits filtering
        train_items: List[DatasetItem] = client.datasets.get_items(
            external_id=conversation_dataset_id, splits=["train"]
        )
        assert len(train_items) == 1
        assert "train" in train_items[0].splits

        test_items: List[DatasetItem] = client.datasets.get_items(external_id=conversation_dataset_id, splits=["test"])
        assert len(test_items) == 1
        assert "test" in test_items[0].splits

        # Test filtering by multiple splits
        train_test_items: List[DatasetItem] = client.datasets.get_items(
            external_id=conversation_dataset_id, splits=["train", "test"]
        )
        assert len(train_test_items) == 1

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
        # Get initial dataset state
        initial_datasets = client.datasets.list()
        initial_dataset = next((d for d in initial_datasets if d.external_id == test_dataset_id), None)
        assert initial_dataset is not None
        initial_revision_id = initial_dataset.latest_revision_id

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

        assert create_items_result.count == 2  # Total items in dataset after first creation
        assert create_items_result.revision_id is not None

        # Verify that creating items created a new dataset revision
        updated_datasets = client.datasets.list()
        updated_dataset = next((d for d in updated_datasets if d.external_id == test_dataset_id), None)
        assert updated_dataset is not None
        assert updated_dataset.latest_revision_id != initial_revision_id
        assert updated_dataset.latest_revision_id == create_items_result.revision_id

        # Add additional items with different splits for testing splits filtering
        additional_items = [
            {
                "Text Field": "Validation text 1",
                "Number Field": 100,
            },
            {
                "Text Field": "Validation text 2",
                "Number Field": 101,
            },
        ]

        validation_result = client.datasets.create_items(
            external_id=test_dataset_id, items=additional_items, split_names=["validation"]
        )

        assert validation_result.count == 4  # Total items in dataset (2 + 2)
        assert validation_result.revision_id is not None
        assert validation_result.revision_id != create_items_result.revision_id

        # Verify that adding more items created another new revision
        final_datasets = client.datasets.list()
        final_dataset = next((d for d in final_datasets if d.external_id == test_dataset_id), None)
        assert final_dataset is not None
        assert final_dataset.latest_revision_id == validation_result.revision_id

    def test_retrieve_items_from_dataset(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test retrieving items from the dataset."""
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id)

        assert len(retrieved_items) == 4  # 2 train/test items + 2 validation items

        # Test splits filtering
        train_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id, splits=["train"])

        assert len(train_items) == 2

        for item in train_items:
            assert "train" in item.splits

        test_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id, splits=["test"])

        assert len(test_items) == 2
        for item in test_items:
            assert "test" in item.splits

        validation_items: List[DatasetItem] = client.datasets.get_items(
            external_id=test_dataset_id, splits=["validation"]
        )
        assert len(validation_items) == 2
        for item in validation_items:
            assert "validation" in item.splits

        # Test filtering by multiple splits
        train_test_items: List[DatasetItem] = client.datasets.get_items(
            external_id=test_dataset_id, splits=["train", "test"]
        )
        assert len(train_test_items) == 2  # Items that have both train AND test splits

        # Test filtering with non-existent split
        empty_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id, splits=["nonexistent"])
        assert len(empty_items) == 0

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

        # Get dataset state before deletion
        pre_delete_datasets = client.datasets.list()
        pre_delete_dataset = next((d for d in pre_delete_datasets if d.external_id == test_dataset_id), None)
        assert pre_delete_dataset is not None
        pre_delete_revision_id = pre_delete_dataset.latest_revision_id

        # Use the new keyword-only arguments
        delete_result = client.datasets.delete_item(
            external_id=test_dataset_id, item_id=TestDatasetItemsOperations.test_item_id
        )

        assert delete_result.success is True

        # Verify that deleting an item created a new dataset revision
        post_delete_datasets = client.datasets.list()
        post_delete_dataset = next((d for d in post_delete_datasets if d.external_id == test_dataset_id), None)
        assert post_delete_dataset is not None
        assert post_delete_dataset.latest_revision_id != pre_delete_revision_id

        # Verify the item is deleted
        retrieved_items: List[DatasetItem] = client.datasets.get_items(external_id=test_dataset_id)

        deleted_item = next(
            (item for item in retrieved_items if item.id == TestDatasetItemsOperations.test_item_id), None
        )

        assert deleted_item is None

    def test_get_items_by_revision(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test retrieving items by specific revision ID."""
        # Create some items to get a revision ID
        items = [
            {
                "Text Field": "Revision test text",
                "Number Field": 999,
            }
        ]

        create_result = client.datasets.create_items(external_id=test_dataset_id, items=items, split_names=["test"])

        assert create_result.revision_id is not None

        # Test get_items_by_revision with the returned revision ID
        revision_items = client.datasets.get_items_by_revision(
            dataset_id=test_dataset_id, revision_id=create_result.revision_id
        )

        assert len(revision_items) > 0
        # Verify we can find our test item in the revision
        test_item = next((item for item in revision_items if item.data.get("Text Field") == "Revision test text"), None)
        assert test_item is not None
        assert test_item.data["Number Field"] == 999

    def test_get_schema_by_version(self, client: AutoblocksAppClient, test_dataset_id: str) -> None:
        """Test retrieving dataset schema by version and verify name field is included."""
        # Get the current dataset to find its schema version
        datasets = client.datasets.list()
        test_dataset = next((d for d in datasets if d.external_id == test_dataset_id), None)
        assert test_dataset is not None
        assert test_dataset.schema_version is not None

        # Get schema by version
        schema = client.datasets.get_schema_by_version(
            dataset_id=test_dataset_id, schema_version=test_dataset.schema_version
        )

        assert schema.id is not None
        assert schema.external_id == test_dataset_id
        assert schema.schema_version == test_dataset.schema_version
        assert schema.name is not None  # Verify the new name field is present
        assert schema.schema_properties is not None
        assert len(schema.schema_properties) > 0
