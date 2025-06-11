"""Datasets API Client."""

import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl.api.base_app_resource_client import BaseAppResourceClient
from autoblocks._impl.api.exceptions import ValidationError
from autoblocks._impl.api.utils.serialization import deserialize_model
from autoblocks._impl.api.utils.serialization import deserialize_model_list
from autoblocks._impl.api.utils.serialization import serialize_model
from autoblocks._impl.datasets.models.dataset import Dataset
from autoblocks._impl.datasets.models.dataset import DatasetItem
from autoblocks._impl.datasets.models.dataset import DatasetItemsSuccessResponse
from autoblocks._impl.datasets.models.dataset import DatasetSchema
from autoblocks._impl.datasets.models.dataset import SuccessResponse
from autoblocks._impl.datasets.models.schema import create_schema_property
from autoblocks._impl.util import cuid_generator

log = logging.getLogger(__name__)


class DatasetsClient(BaseAppResourceClient):
    """Datasets API Client"""

    def __init__(self, app_slug: str, api_key: str, timeout: timedelta = timedelta(seconds=60)) -> None:
        super().__init__(app_slug=app_slug, api_key=api_key, timeout=timeout)

    def list(self) -> List[Dataset]:
        """
        List all datasets in the app.

        Returns:
            List of datasets
        """
        path = self._build_app_path("datasets")
        response = self._make_request("GET", path)
        return deserialize_model_list(Dataset, response)

    def create(
        self,
        *,
        name: str,
        schema: List[Dict[str, Any]],
    ) -> Dataset:
        """
        Create a new dataset.

        Args:
            name: Dataset name (required)
            schema: Dataset schema as a list of property dictionaries (required)

        Returns:
            Created dataset

        Raises:
            ValidationError: If required parameters are missing or invalid
        """
        # Construct the basic dataset data
        data: Dict[str, Any] = {"name": name}

        # Process schema items
        processed_schema = []

        for i, prop_dict in enumerate(schema):
            prop_dict_copy = dict(prop_dict)

            if "id" not in prop_dict_copy:
                prop_dict_copy["id"] = cuid_generator()

            try:
                # 3. If valid, add to processed schema
                schema_prop = create_schema_property(prop_dict_copy)
                processed_schema.append(serialize_model(schema_prop))
            except Exception as e:
                raise ValidationError(f"Invalid schema property at index {i}: {str(e)}")

        # Use the field alias to ensure it's sent as 'schema' to the API
        data["schema"] = processed_schema

        # Make the API call
        path = self._build_app_path("datasets")
        response = self._make_request("POST", path, data)
        return deserialize_model(Dataset, response)

    def destroy(
        self,
        *,
        external_id: str,
    ) -> SuccessResponse:
        """
        Delete a dataset.

        Args:
            external_id: Dataset ID (required)

        Returns:
            Success response

        Raises:
            ValidationError: If dataset ID is not provided
        """
        if not external_id:
            raise ValidationError("External ID is required")

        path = self._build_app_path("datasets", external_id)
        response = self._make_request("DELETE", path)
        return deserialize_model(SuccessResponse, response)

    def get_items(
        self,
        *,
        external_id: str,
        splits: Optional[List[str]] = None,
    ) -> List[DatasetItem]:
        """
        Get all items in a dataset.

        Args:
            external_id: Dataset ID (required)
            splits: Optional list of splits to filter by

        Returns:
            List of dataset items

        Raises:
            ValidationError: If dataset ID is not provided
        """
        if not external_id:
            raise ValidationError("Dataset ID is required")

        query_params: Dict[str, Any] = {}
        if splits:
            query_params["splits"] = ",".join(splits)

        path = self._build_app_path("datasets", external_id, "items", **query_params)
        response = self._make_request("GET", path)
        return deserialize_model_list(DatasetItem, response)

    def create_items(
        self,
        *,
        external_id: str,
        items: List[Dict[str, Any]],
        split_names: Optional[List[str]] = None,
    ) -> DatasetItemsSuccessResponse:
        """
        Create items in a dataset.

        Args:
            external_id: Dataset ID (required)
            items: List of item dictionaries to create (required)
            split_names: Optional list of split names to assign items to

        Returns:
            Success response with count and revision ID

        Raises:
            ValidationError: If external_id is empty
        """
        if not external_id:
            raise ValidationError("External ID is required")

        # Prepare data payload
        data: Dict[str, Any] = {"items": items}

        # Add split names at the request level if provided
        if split_names:
            data["splitNames"] = split_names

        path = self._build_app_path("datasets", external_id, "items")
        response = self._make_request("POST", path, data)
        return deserialize_model(DatasetItemsSuccessResponse, response)

    def get_schema_by_version(self, *, dataset_id: str, schema_version: int) -> DatasetSchema:
        """
        Get a specific version of a dataset schema.

        Args:
            dataset_id: Dataset ID
            schema_version: Schema version number

        Returns:
            Dataset schema for the specified version
        """
        path = self._build_app_path("datasets", dataset_id, "schema", str(schema_version))
        response = self._make_request("GET", path)
        return deserialize_model(DatasetSchema, response)

    def get_items_by_revision(
        self, *, dataset_id: str, revision_id: str, splits: Optional[List[str]] = None
    ) -> List[DatasetItem]:
        """
        Get items from a specific revision of a dataset.

        Args:
            dataset_id: Dataset ID
            revision_id: Revision ID
            splits: Optional list of splits to filter by

        Returns:
            List of dataset items from the specified revision
        """
        query_params: Dict[str, Any] = {}
        if splits:
            query_params["splits"] = ",".join(splits)

        path = self._build_app_path("datasets", dataset_id, "revisions", revision_id, "items", **query_params)
        response = self._make_request("GET", path)
        return deserialize_model_list(DatasetItem, response)

    def get_items_by_schema_version(
        self, *, dataset_id: str, schema_version: int, splits: Optional[List[str]] = None
    ) -> List[DatasetItem]:
        """
        Get items with a specific schema version.

        Args:
            dataset_id: Dataset ID
            schema_version: Schema version
            splits: Optional list of splits to filter by

        Returns:
            List of dataset items with the specified schema version
        """
        query_params: Dict[str, Any] = {}
        if splits:
            query_params["splits"] = ",".join(splits)

        path = self._build_app_path("datasets", dataset_id, "schema", str(schema_version), "items", **query_params)
        response = self._make_request("GET", path)
        return deserialize_model_list(DatasetItem, response)

    def update_item(
        self,
        *,
        external_id: str,
        item_id: str,
        data: Dict[str, Any],
        split_names: Optional[List[str]] = None,
    ) -> SuccessResponse:
        """
        Update an item in a dataset.

        Args:
            external_id: Dataset ID (required)
            item_id: Item ID (required)
            data: Update data for the item (required)
            split_names: Optional list of split names to assign item to (replaces existing splits)

        Returns:
            Success response

        Raises:
            ValidationError: If external_id, item_id, or data are not provided
        """
        if not external_id:
            raise ValidationError("External ID is required")
        if not item_id:
            raise ValidationError("Item ID is required")

        # Prepare the update request
        update_request: Dict[str, Any] = {"data": data}

        # Add split names if provided
        if split_names:
            update_request["splitNames"] = split_names

        path = self._build_app_path("datasets", external_id, "items", item_id)
        response = self._make_request("PUT", path, update_request)
        return deserialize_model(SuccessResponse, response)

    def delete_item(
        self,
        *,
        external_id: str,
        item_id: str,
    ) -> SuccessResponse:
        """
        Delete an item from a dataset.

        Args:
            external_id: Dataset ID (required)
            item_id: Item ID (required)

        Returns:
            Success response

        Raises:
            ValidationError: If external_id or item_id are not provided
        """
        if not external_id:
            raise ValidationError("External ID is required")
        if not item_id:
            raise ValidationError("Item ID is required")

        path = self._build_app_path("datasets", external_id, "items", item_id)
        response = self._make_request("DELETE", path)
        return deserialize_model(SuccessResponse, response)


def create_datasets_client(api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> DatasetsClient:
    """
    Create a DatasetsClient instance.

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout: Request timeout as timedelta (default: 60 seconds)

    Returns:
        DatasetsClient instance
    """
    return DatasetsClient(api_key=api_key, app_slug=app_slug, timeout=timeout)
