"""Datasets V2 API Client."""

import functools
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.datasets_v2.exceptions import APIError
from autoblocks._impl.datasets_v2.exceptions import AuthenticationError
from autoblocks._impl.datasets_v2.exceptions import RateLimitError
from autoblocks._impl.datasets_v2.exceptions import ResourceNotFoundError
from autoblocks._impl.datasets_v2.exceptions import ValidationError
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetItemsV2Request
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetV2Request
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemsResponseV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemsSuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetListItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetSchemaV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetV2
from autoblocks._impl.datasets_v2.models.dataset import SuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import UpdateItemV2Request
from autoblocks._impl.datasets_v2.utils.helpers import batch
from autoblocks._impl.datasets_v2.utils.helpers import build_path
from autoblocks._impl.datasets_v2.utils.serialization import deserialize_model
from autoblocks._impl.datasets_v2.utils.serialization import deserialize_model_list
from autoblocks._impl.datasets_v2.utils.serialization import serialize_model

log = logging.getLogger(__name__)

T = TypeVar("T")


def require_model(model_class: Type[Any]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to validate that the first argument after self is an instance of model_class.

    Args:
        model_class: The expected model class

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Get the first argument after self
            if args and len(args) > 0:
                arg = args[0]
                if not isinstance(arg, model_class):
                    raise TypeError(f"Expected {model_class.__name__}, got {type(arg).__name__}")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class DatasetsV2Client:
    """Datasets V2 API Client"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the client with configuration

        Args:
            config: Dict with:
                - api_key: Autoblocks API key
                - app_slug: Application slug
                - timeout_ms: Optional timeout in milliseconds (default: 60000)
        """
        if not config.get("api_key"):
            raise ValidationError("API key is required")

        if not config.get("app_slug"):
            raise ValidationError("App slug is required")

        self.api_key = config["api_key"]
        self.app_slug = config["app_slug"]
        self.timeout_sec = config.get("timeout_ms", 60000) / 1000  # Convert to seconds
        self.base_url = API_ENDPOINT_V2

        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Create a shared client for connection pooling
        self._client = httpx.Client(headers=self._headers, timeout=self.timeout_sec)

    def __enter__(self) -> "DatasetsV2Client":
        """Support for context manager protocol"""
        return self

    def __exit__(self, exc_type: Optional[Type[Exception]], exc_value: Optional[Exception], traceback: Any) -> None:
        """Close the client when exiting context"""
        self.close()

    def close(self) -> None:
        """Close the HTTP client"""
        if hasattr(self, "_client") and self._client:
            self._client.close()

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
        status_code = response.status_code
        error_info = {}

        # Try to parse error details from response
        try:
            error_info = response.json()
        except Exception:
            # If parsing fails, use the response text
            error_info = {"message": response.text}

        message = error_info.get("message", response.reason_phrase)

        if status_code == 401:
            raise AuthenticationError(message, response)
        elif status_code == 404:
            # Try to extract resource info from URL
            url_parts = response.url.path.split("/")
            resource_type = url_parts[-2] if len(url_parts) >= 2 else "Resource"
            resource_id = url_parts[-1] if len(url_parts) >= 1 else "unknown"
            raise ResourceNotFoundError(resource_type, resource_id, response)
        elif status_code == 429:
            raise RateLimitError(message, response)
        else:
            raise APIError(status_code, message, response, error_info)

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
        url = f"{self.base_url}{path}"

        # If the data is a Pydantic model, serialize it
        json_data: Optional[Any] = None
        if data is not None and hasattr(data, "model_dump"):
            json_data = serialize_model(data)
        else:
            json_data = data

        try:
            response = self._client.request(
                method=method,
                url=url,
                json=json_data,
            )

            # Handle error responses
            if response.is_error:
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

    def list(self) -> List[DatasetListItemV2]:
        """
        List all datasets in the app.

        Returns:
            List of dataset items
        """
        path = self._build_app_path("datasets")
        response = self._make_request("GET", path)
        return deserialize_model_list(response, DatasetListItemV2)

    @require_model(CreateDatasetV2Request)
    def create(self, dataset: CreateDatasetV2Request) -> DatasetV2:
        """
        Create a new dataset.

        Args:
            dataset: Dataset creation request

        Returns:
            Created dataset
        """
        path = self._build_app_path("datasets")
        response = self._make_request("POST", path, dataset)
        return deserialize_model(response, DatasetV2)

    def destroy(self, external_id: str) -> SuccessResponse:
        """
        Delete a dataset.

        Args:
            external_id: Dataset external ID

        Returns:
            Operation result with success flag
        """
        path = self._build_app_path("datasets", external_id)
        result = self._make_request("DELETE", path)
        if result is None or not isinstance(result, dict):
            return SuccessResponse(success=True)  # Assume success if no error
        return deserialize_model(result, SuccessResponse)

    def get_items(self, external_id: str) -> List[DatasetItemV2]:
        """
        Get all items for a dataset.

        Args:
            external_id: Dataset external ID

        Returns:
            List of dataset items
        """
        path = self._build_app_path("datasets", external_id, "items")
        response = self._make_request("GET", path)

        # Check if the response is in the DatasetItemsResponseV2 format
        if response and isinstance(response, dict) and "items" in response:
            dataset_response = deserialize_model(response, DatasetItemsResponseV2)
            return dataset_response.items

        # Otherwise, assume it's a direct list of items
        return deserialize_model_list(response, DatasetItemV2)

    @require_model(CreateDatasetItemsV2Request)
    def create_items(self, external_id: str, request: CreateDatasetItemsV2Request) -> DatasetItemsSuccessResponse:
        """
        Add items to a dataset.

        Args:
            external_id: Dataset external ID
            request: Items creation request

        Returns:
            Success response with count and revision ID
        """
        path = self._build_app_path("datasets", external_id, "items")
        result = self._make_request("POST", path, request)
        if result is None or not isinstance(result, dict):
            return DatasetItemsSuccessResponse(count=0, revisionId="")
        return deserialize_model(result, DatasetItemsSuccessResponse)

    def get_schema_by_version(self, external_id: str, schema_version: int) -> DatasetSchemaV2:
        """
        Get schema for a specific version.

        Args:
            external_id: Dataset external ID
            schema_version: Schema version

        Returns:
            Dataset schema
        """
        path = self._build_app_path("datasets", external_id, "schema-versions", str(schema_version))
        response = self._make_request("GET", path)
        return deserialize_model(response, DatasetSchemaV2)

    def get_items_by_revision(
        self, external_id: str, revision_id: str, splits: Optional[List[str]] = None
    ) -> List[DatasetItemV2]:
        """
        Get items by revision ID.

        Args:
            external_id: Dataset external ID
            revision_id: Revision ID
            splits: Optional list of split names to filter by

        Returns:
            List of dataset items
        """
        query_params = {"splits": splits} if splits else None
        path = self._build_app_path("datasets", external_id, "revisions", revision_id, query_params=query_params)
        response = self._make_request("GET", path)

        # Check if the response is in the DatasetItemsResponseV2 format
        if response and isinstance(response, dict) and "items" in response:
            dataset_response = deserialize_model(response, DatasetItemsResponseV2)
            return dataset_response.items

        # Otherwise, assume it's a direct list of items
        return deserialize_model_list(response, DatasetItemV2)

    def get_items_by_schema_version(
        self, external_id: str, schema_version: int, splits: Optional[List[str]] = None
    ) -> List[DatasetItemV2]:
        """
        Get items by schema version.

        Args:
            external_id: Dataset external ID
            schema_version: Schema version
            splits: Optional list of split names to filter by

        Returns:
            List of dataset items
        """
        query_params = {"splits": splits} if splits else None
        path = self._build_app_path(
            "datasets", external_id, "schema-versions", str(schema_version), "items", query_params=query_params
        )
        response = self._make_request("GET", path)

        # Check if the response is in the DatasetItemsResponseV2 format
        if response and isinstance(response, dict) and "items" in response:
            dataset_response = deserialize_model(response, DatasetItemsResponseV2)
            return dataset_response.items

        # Otherwise, assume it's a direct list of items
        return deserialize_model_list(response, DatasetItemV2)

    @require_model(UpdateItemV2Request)
    def update_item(self, external_id: str, item_id: str, request: UpdateItemV2Request) -> SuccessResponse:
        """
        Update a dataset item.

        Args:
            external_id: Dataset external ID
            item_id: Item ID
            request: Update request

        Returns:
            Success response with success flag
        """
        path = self._build_app_path("datasets", external_id, "items", item_id)
        result = self._make_request("PUT", path, request)
        if result is None or not isinstance(result, dict):
            return SuccessResponse(success=True)  # Assume success if no error
        return deserialize_model(result, SuccessResponse)

    def delete_item(self, external_id: str, item_id: str) -> SuccessResponse:
        """
        Delete a dataset item.

        Args:
            external_id: Dataset external ID
            item_id: Item ID

        Returns:
            Success response with success flag
        """
        path = self._build_app_path("datasets", external_id, "items", item_id)
        result = self._make_request("DELETE", path)
        if result is None or not isinstance(result, dict):
            return SuccessResponse(success=True)  # Assume success if no error
        return deserialize_model(result, SuccessResponse)

    def batch_create_items(
        self,
        external_id: str,
        items: List[Dict[str, Any]],
        split_names: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> List[DatasetItemsSuccessResponse]:
        """
        Create items in batches to avoid large payloads.

        Args:
            external_id: Dataset external ID
            items: List of items to create
            split_names: Optional list of split names
            batch_size: Size of each batch

        Returns:
            List of operation results containing count and revision IDs
        """
        results = []
        batched_items = batch(items, batch_size)

        for item_batch in batched_items:
            request = CreateDatasetItemsV2Request(items=item_batch, splitNames=split_names)
            result = self.create_items(external_id, request)
            results.append(result)

        return results


def create_datasets_v2_client(api_key: str, app_slug: str, timeout_ms: int = 60000) -> DatasetsV2Client:
    """
    Create a new datasets v2 client

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout_ms: Optional timeout in milliseconds (default: 60000)

    Returns:
        A DatasetsV2Client instance
    """
    config = {"api_key": api_key, "app_slug": app_slug, "timeout_ms": timeout_ms}
    return DatasetsV2Client(config)
