"""Datasets client implementation for AutoblocksAPIClient."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Union

from autoblocks._impl.datasets_v2.client import DatasetsV2Client
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetItemsV2Request
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetV2Request
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemsSuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetListItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetSchemaV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetV2
from autoblocks._impl.datasets_v2.models.dataset import SuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import UpdateItemV2Request
from autoblocks._impl.datasets_v2.models.schema import SchemaProperty
from autoblocks._impl.datasets_v2.models.schema import SchemaPropertyType


class Datasets:
    """Datasets client for AutoblocksAPIClient that wraps the DatasetsV2Client."""

    def __init__(self, api_key: str, app_slug: str, timeout_ms: int = 60000) -> None:
        """
        Initialize the datasets client.

        Args:
            api_key: Autoblocks API key
            app_slug: Application slug
            timeout_ms: Request timeout in milliseconds
        """
        self._client = DatasetsV2Client(
            {
                "api_key": api_key,
                "app_slug": app_slug,
                "timeout_ms": timeout_ms,
            }
        )

    def create_schema_property(
        self, *, property_type: SchemaPropertyType, name: str, required: bool = True, **kwargs: Any
    ) -> SchemaProperty:
        """
        Helper to create schema properties with auto-generated IDs.

        Args:
            property_type: The type of schema property
            name: The name of the property
            required: Whether the property is required (default: True)
            **kwargs: Additional property-specific arguments

        Returns:
            A schema property instance
        """
        return self._client.create_schema_property(property_type=property_type, name=name, required=required, **kwargs)

    def list(self) -> List[DatasetListItemV2]:
        """
        List all datasets in the app.

        Returns:
            List of dataset items
        """
        return self._client.list()

    def create(
        self,
        dataset: Optional[Union[CreateDatasetV2Request, Dict[str, Any]]] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[Sequence[Union[Dict[str, Any], SchemaProperty]]] = None,
    ) -> DatasetV2:
        """
        Create a new dataset.

        Args:
            dataset: Dataset creation request object or dictionary
            name: Dataset name (ignored if dataset is provided)
            description: Dataset description (ignored if dataset is provided)
            schema: Dataset schema properties (ignored if dataset is provided)

        Returns:
            Created dataset
        """
        return self._client.create(dataset, name=name, description=description, schema=schema)

    def destroy(self, dataset_id: Optional[str] = None, *, dataset_id_kwarg: Optional[str] = None) -> SuccessResponse:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset external ID (positional argument for backward compatibility)
            dataset_id_kwarg: Dataset external ID (keyword argument)

        Returns:
            Success response
        """
        return self._client.destroy(dataset_id, dataset_id_kwarg=dataset_id_kwarg)

    def get_items(
        self, dataset_id: Optional[str] = None, *, dataset_id_kwarg: Optional[str] = None
    ) -> List[DatasetItemV2]:
        """
        Get all items in a dataset.

        Args:
            dataset_id: Dataset external ID (positional argument for backward compatibility)
            dataset_id_kwarg: Dataset external ID (keyword argument)

        Returns:
            List of dataset items
        """
        return self._client.get_items(dataset_id, dataset_id_kwarg=dataset_id_kwarg)

    def create_items(
        self,
        items: Optional[Union[CreateDatasetItemsV2Request, Dict[str, Any], List[Dict[str, Any]]]] = None,
        dataset_id: Optional[str] = None,
        *,
        items_kwarg: Optional[Union[CreateDatasetItemsV2Request, Dict[str, Any], List[Dict[str, Any]]]] = None,
        dataset_id_kwarg: Optional[str] = None,
        split_names: Optional[List[str]] = None,
    ) -> DatasetItemsSuccessResponse:
        """
        Create items in a dataset.

        Args:
            items: Items creation request object, dictionary, or list of item dictionaries (positional)
            dataset_id: Dataset external ID (positional for backward compatibility)
            items_kwarg: Items creation request object, dictionary, or list of item dictionaries
            dataset_id_kwarg: Dataset external ID
            split_names: Optional list of split names

        Returns:
            Success response with count and revision ID
        """
        return self._client.create_items(
            items, dataset_id, items_kwarg=items_kwarg, dataset_id_kwarg=dataset_id_kwarg, split_names=split_names
        )

    def get_schema_by_version(self, *, dataset_id: str, schema_version: int) -> DatasetSchemaV2:
        """
        Get dataset schema by version.

        Args:
            dataset_id: Dataset external ID
            schema_version: Schema version

        Returns:
            Dataset schema
        """
        return self._client.get_schema_by_version(dataset_id=dataset_id, schema_version=schema_version)

    def get_items_by_revision(
        self, *, dataset_id: str, revision_id: str, splits: Optional[List[str]] = None
    ) -> List[DatasetItemV2]:
        """
        Get dataset items by revision ID.

        Args:
            dataset_id: Dataset external ID
            revision_id: Revision ID
            splits: Optional list of split names to filter by

        Returns:
            List of dataset items
        """
        return self._client.get_items_by_revision(dataset_id=dataset_id, revision_id=revision_id, splits=splits)

    def get_items_by_schema_version(
        self, *, dataset_id: str, schema_version: int, splits: Optional[List[str]] = None
    ) -> List[DatasetItemV2]:
        """
        Get dataset items by schema version.

        Args:
            dataset_id: Dataset external ID
            schema_version: Schema version
            splits: Optional list of split names to filter by

        Returns:
            List of dataset items
        """
        return self._client.get_items_by_schema_version(
            dataset_id=dataset_id, schema_version=schema_version, splits=splits
        )

    def update_item(
        self,
        dataset_id: Optional[str] = None,
        item_id: Optional[str] = None,
        data: Optional[Union[UpdateItemV2Request, Dict[str, Any]]] = None,
        *,
        dataset_id_kwarg: Optional[str] = None,
        item_id_kwarg: Optional[str] = None,
        data_kwarg: Optional[Union[UpdateItemV2Request, Dict[str, Any]]] = None,
        split_names: Optional[List[str]] = None,
    ) -> SuccessResponse:
        """
        Update a dataset item.

        Args:
            dataset_id: Dataset external ID (positional for backward compatibility)
            item_id: Item ID (positional for backward compatibility)
            data: Update request object or dictionary with item data (positional)
            dataset_id_kwarg: Dataset external ID
            item_id_kwarg: Item ID
            data_kwarg: Update request object or dictionary with item data
            split_names: Optional list of split names

        Returns:
            Success response
        """
        return self._client.update_item(
            dataset_id,
            item_id,
            data,
            dataset_id_kwarg=dataset_id_kwarg,
            item_id_kwarg=item_id_kwarg,
            data_kwarg=data_kwarg,
            split_names=split_names,
        )

    def delete_item(
        self,
        dataset_id: Optional[str] = None,
        item_id: Optional[str] = None,
        *,
        dataset_id_kwarg: Optional[str] = None,
        item_id_kwarg: Optional[str] = None,
    ) -> SuccessResponse:
        """
        Delete a dataset item.

        Args:
            dataset_id: Dataset external ID (positional for backward compatibility)
            item_id: Item ID (positional for backward compatibility)
            dataset_id_kwarg: Dataset external ID
            item_id_kwarg: Item ID

        Returns:
            Success response
        """
        return self._client.delete_item(
            dataset_id, item_id, dataset_id_kwarg=dataset_id_kwarg, item_id_kwarg=item_id_kwarg
        )

    def batch_create_items(
        self,
        *,
        dataset_id: str,
        items: List[Dict[str, Any]],
        split_names: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> List[DatasetItemsSuccessResponse]:
        """
        Create items in batches to avoid request size limits.

        Args:
            dataset_id: Dataset external ID
            items: List of item dictionaries
            split_names: Optional list of split names
            batch_size: Batch size (default: 100)

        Returns:
            List of success responses for each batch
        """
        return self._client.batch_create_items(
            dataset_id=dataset_id, items=items, split_names=split_names, batch_size=batch_size
        )

    # Enable context manager support via delegation to the underlying client
    def __enter__(self) -> "Datasets":
        self._client.__enter__()
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Any) -> None:
        self._client.__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        """Close the underlying client."""
        self._client.close()
