"""Datasets API Client."""

import json
import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.datasets.exceptions import APIError
from autoblocks._impl.datasets.exceptions import ValidationError
from autoblocks._impl.datasets.exceptions import parse_error_response
from autoblocks._impl.datasets.models.dataset import Dataset
from autoblocks._impl.datasets.models.dataset import DatasetItem
from autoblocks._impl.datasets.models.dataset import DatasetItemsSuccessResponse
from autoblocks._impl.datasets.models.dataset import DatasetListItem
from autoblocks._impl.datasets.models.dataset import DatasetSchema
from autoblocks._impl.datasets.models.dataset import SuccessResponse
from autoblocks._impl.datasets.models.schema import create_schema_property
from autoblocks._impl.datasets.utils.helpers import build_path
from autoblocks._impl.datasets.utils.serialization import deserialize_model
from autoblocks._impl.datasets.utils.serialization import deserialize_model_list
from autoblocks._impl.datasets.utils.serialization import serialize_model
from autoblocks._impl.util import cuid_generator

log = logging.getLogger(__name__)


class DatasetsClient:
    """Datasets API Client"""

    def __init__(self, api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> None:
        """
        Initialize the client with configuration

        Args:
            api_key: Autoblocks API key
            app_slug: Application slug
            timeout: Optional timeout as timedelta (default: 60 seconds)
        """
        if not api_key:
            raise ValidationError("API key is required")

        if not app_slug:
            raise ValidationError("App slug is required")

        self.api_key = api_key
        self.app_slug = app_slug
        self.timeout = timeout
        self.base_url = API_ENDPOINT_V2

        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Create a shared client for connection pooling
        self._client = httpx.Client(headers=self._headers, timeout=self.timeout.total_seconds())

    def _build_app_path(self, *segments: str, **query_params: Any) -> str:
        """
        Build a path with app slug prefix.

        Args:
            *segments: Path segments
            **query_params: Query parameters

        Returns:
            Full path
        """
        return build_path("apps", self.app_slug, *segments, query_params=query_params)

    def _handle_response_error(self, response: httpx.Response) -> None:
        """
        Handle HTTP error response.

        Args:
            response: HTTP response

        Raises:
            AuthenticationError: For 401 Unauthorized
            ResourceNotFoundError: For 404 Not Found
            RateLimitError: For 429 Too Many Requests
            APIError: For other errors
        """
        # Parse error response and raise appropriate exception
        raise parse_error_response(response)

    def _make_request(self, method: str, path: str, data: Optional[Any] = None) -> Any:
        """
        Make HTTP request to the API.

        Args:
            method: HTTP method
            path: API path
            data: Optional request data

        Returns:
            Response data

        Raises:
            APIError: If the request fails
        """
        url = f"{self.base_url}/{path}"

        # If the data is a Pydantic model, serialize it
        json_data: Optional[Any] = None
        if data is not None and hasattr(data, "model_dump"):
            json_data = serialize_model(data)
        else:
            json_data = data

        # Log request details at debug level
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Request: {method} {url}")
            if json_data:
                log.debug(f"Request Data: {json.dumps(json_data, indent=2)}")

        try:
            response = self._client.request(
                method=method,
                url=url,
                json=json_data,
            )

            # Log response details at debug level
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"Response Status: {response.status_code}")
                log.debug(f"Response Headers: {dict(response.headers)}")
                if response.content:
                    try:
                        response_json = response.json()
                        log.debug(f"Response Body: {json.dumps(response_json, indent=2)}")
                    except Exception:  # Handle all exceptions but with a type
                        log.debug(f"Response Body (text): {response.text}")

            # Handle error responses with better debugging
            if response.is_error:
                if response.status_code == 400:
                    try:
                        error_content = response.json()
                        log.error(f"Error response (400 Bad Request): {json.dumps(error_content, indent=2)}")
                    except Exception as e:
                        log.error(f"Error response (400 Bad Request): {response.text}")
                        log.error(f"Failed to parse JSON: {str(e)}")

                self._handle_response_error(response)

            # Parse and return the response
            if response.content and response.content.strip():
                result = response.json()
                if result is None:
                    return {}  # Return empty dict instead of None
                return result
            return {}  # Return empty dict for empty responses

        except httpx.HTTPStatusError as e:
            self._handle_response_error(e.response)
        except httpx.RequestError as e:
            # Network errors, timeouts, etc.
            raise APIError(0, f"Request failed: {str(e)}")

    def list(self) -> List[DatasetListItem]:
        """
        List all datasets in the app.

        Returns:
            List of datasets
        """
        path = self._build_app_path("datasets")
        response = self._make_request("GET", path)
        return deserialize_model_list(DatasetListItem, response)

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
    ) -> List[DatasetItem]:
        """
        Get all items in a dataset.

        Args:
            external_id: Dataset ID (required)

        Returns:
            List of dataset items

        Raises:
            ValidationError: If dataset ID is not provided
        """
        if not external_id:
            raise ValidationError("Dataset ID is required")

        path = self._build_app_path("datasets", external_id, "items")
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

        path = self._build_app_path(
            "datasets", dataset_id, "revisions", revision_id, "items", query_params=query_params
        )
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

        path = self._build_app_path(
            "datasets", dataset_id, "schema", str(schema_version), "items", query_params=query_params
        )
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
