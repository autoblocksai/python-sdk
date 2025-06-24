"""Tests for AutoblocksAppClient dataset deserialization with defaultValue fields."""

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks.api.app_client import AutoblocksAppClient


def test_dataset_deserialization_with_default_value(httpx_mock):
    """Test that datasets with defaultValue field in schema properties can be deserialized correctly."""
    # This test reproduces the exact error scenario from the user's issue
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app/datasets",
        method="GET",
        status_code=200,
        json=[
            {
                "id": "dataset-id-1",
                "externalId": "test-dataset",
                "name": "Test Dataset",
                "createdAt": "2023-01-01T00:00:00Z",
                "latestRevisionId": "revision-1",
                "schemaVersion": 1,
                "schema": [
                    {
                        "id": "string-prop-id",
                        "name": "String Property",
                        "type": "String",
                        "required": True,
                    },
                    {
                        "id": "s23p00ugn0gb5zhmg123",
                        "name": "Number Property",
                        "type": "Number",
                        "required": False,
                        "defaultValue": 30,  # This was causing the validation error
                    },
                    {
                        "id": "select-prop-id",
                        "name": "Select Property",
                        "type": "Select",
                        "required": False,
                        "options": ["option1", "option2"],
                        "defaultValue": "option1",
                    },
                ],
            }
        ],
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAppClient(app_slug="test-app", api_key="mock-api-key")
    datasets = client.datasets.list()

    # Verify the dataset was deserialized successfully
    assert len(datasets) == 1
    dataset = datasets[0]

    assert dataset.id == "dataset-id-1"
    assert dataset.external_id == "test-dataset"
    assert dataset.name == "Test Dataset"
    assert dataset.schema_version == 1

    # Verify schema properties were parsed correctly
    assert dataset.schema_properties is not None
    assert len(dataset.schema_properties) == 3

    # Check string property
    string_prop = dataset.schema_properties[0]
    assert string_prop.id == "string-prop-id"
    assert string_prop.name == "String Property"
    assert string_prop.type.value == "String"
    assert string_prop.required is True
    assert string_prop.default_value is None

    # Check number property with defaultValue
    number_prop = dataset.schema_properties[1]
    assert number_prop.id == "s23p00ugn0gb5zhmg123"
    assert number_prop.name == "Number Property"
    assert number_prop.type.value == "Number"
    assert number_prop.required is False
    assert number_prop.default_value == 30

    # Check select property with defaultValue
    select_prop = dataset.schema_properties[2]
    assert select_prop.id == "select-prop-id"
    assert select_prop.name == "Select Property"
    assert select_prop.type.value == "Select"
    assert select_prop.required is False
    assert select_prop.default_value == "option1"
    # Type check to ensure we have a SelectProperty before accessing options
    from autoblocks._impl.datasets.models.schema import SelectProperty

    assert isinstance(select_prop, SelectProperty)
    assert select_prop.options == ["option1", "option2"]


def test_dataset_deserialization_with_invalid_schema_property():
    """Test that datasets with invalid schema properties are handled gracefully."""
    from autoblocks._impl.api.utils.serialization import deserialize_model
    from autoblocks._impl.datasets.models.dataset import Dataset

    # Mock data with an invalid schema property that should be skipped
    dataset_data = {
        "id": "dataset-id-1",
        "externalId": "test-dataset",
        "name": "Test Dataset",
        "schema": [
            {
                "id": "valid-prop-id",
                "name": "Valid Property",
                "type": "String",
                "required": True,
            },
            {
                "id": "invalid-prop-id",
                "name": "Invalid Property",
                "type": "UnknownType",  # This should cause the property to be skipped
                "required": False,
            },
            {
                "id": "another-valid-prop-id",
                "name": "Another Valid Property",
                "type": "Number",
                "required": False,
                "defaultValue": 42,
            },
        ],
    }

    # This should not raise an exception
    dataset = deserialize_model(Dataset, dataset_data)

    # Verify the dataset was created successfully
    assert dataset.id == "dataset-id-1"
    assert dataset.external_id == "test-dataset"
    assert dataset.name == "Test Dataset"

    # Should have only 2 valid properties (invalid one skipped)
    assert dataset.schema_properties is not None
    assert len(dataset.schema_properties) == 2

    # Check that valid properties are present
    prop_names = [prop.name for prop in dataset.schema_properties]
    assert "Valid Property" in prop_names
    assert "Another Valid Property" in prop_names
    assert "Invalid Property" not in prop_names


def test_dataset_schema_property_factory_function():
    """Test the schema property factory function directly."""
    from autoblocks._impl.datasets.models.schema import SchemaPropertyType
    from autoblocks._impl.datasets.models.schema import SelectProperty
    from autoblocks._impl.datasets.models.schema import create_schema_property

    # Test creating a number property with defaultValue
    number_prop_data = {
        "id": "test-number-prop",
        "name": "Test Number",
        "type": "Number",
        "required": False,
        "defaultValue": 42,
    }

    number_prop = create_schema_property(number_prop_data)
    assert number_prop.id == "test-number-prop"
    assert number_prop.name == "Test Number"
    assert number_prop.type == SchemaPropertyType.NUMBER
    assert number_prop.required is False
    assert number_prop.default_value == 42

    # Test creating a select property with defaultValue
    select_prop_data = {
        "id": "test-select-prop",
        "name": "Test Select",
        "type": "Select",
        "required": True,
        "options": ["option1", "option2", "option3"],
        "defaultValue": "option2",
    }

    select_prop = create_schema_property(select_prop_data)
    assert select_prop.id == "test-select-prop"
    assert select_prop.name == "Test Select"
    assert select_prop.type == SchemaPropertyType.SELECT
    assert select_prop.required is True
    assert select_prop.default_value == "option2"
    # Type check before accessing options
    assert isinstance(select_prop, SelectProperty)
    assert select_prop.options == ["option1", "option2", "option3"]

    # Test creating a string property without defaultValue
    string_prop_data = {
        "id": "test-string-prop",
        "name": "Test String",
        "type": "String",
        "required": True,
    }

    string_prop = create_schema_property(string_prop_data)
    assert string_prop.id == "test-string-prop"
    assert string_prop.name == "Test String"
    assert string_prop.type == SchemaPropertyType.STRING
    assert string_prop.required is True
    assert string_prop.default_value is None
