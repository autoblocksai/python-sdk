"""Datasets V2 API Client."""

import functools
import json
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Type
from typing import TypeVar
from typing import Union

import httpx
from pydantic import BaseModel

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.datasets_v2.exceptions import APIError
from autoblocks._impl.datasets_v2.exceptions import ValidationError
from autoblocks._impl.datasets_v2.exceptions import parse_error_response
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetItemsV2Request
from autoblocks._impl.datasets_v2.models.dataset import CreateDatasetV2Request
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemsSuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import DatasetItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetListItemV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetSchemaV2
from autoblocks._impl.datasets_v2.models.dataset import DatasetV2
from autoblocks._impl.datasets_v2.models.dataset import SuccessResponse
from autoblocks._impl.datasets_v2.models.dataset import UpdateItemV2Request
from autoblocks._impl.datasets_v2.models.schema import PROPERTY_TYPE_MAP
from autoblocks._impl.datasets_v2.models.schema import SchemaProperty
from autoblocks._impl.datasets_v2.models.schema import SchemaPropertyType
from autoblocks._impl.datasets_v2.utils.helpers import batch
from autoblocks._impl.datasets_v2.utils.helpers import build_path
from autoblocks._impl.datasets_v2.utils.serialization import deserialize_model
from autoblocks._impl.datasets_v2.utils.serialization import deserialize_model_list
from autoblocks._impl.datasets_v2.utils.serialization import serialize_model
from autoblocks._impl.util import cuid_generator

log = logging.getLogger(__name__)

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="BaseModel")


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

        print(f"URL: {url}")

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
                        print(f"Error response (400 Bad Request): {json.dumps(error_content, indent=2)}")
                    except Exception as e:
                        print(f"Error response (400 Bad Request): {response.text}")
                        print(f"Failed to parse JSON: {str(e)}")

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
        property_id = kwargs.pop("id", cuid_generator())

        # Get the property class from the type mapping
        prop_class = PROPERTY_TYPE_MAP.get(property_type)
        if not prop_class:
            raise ValueError(f"Unknown schema property type: {property_type}")

        # Create a properly formed property dict
        property_data = {
            "id": property_id,
            "name": name,
            "type": property_type.value,  # Use string value of enum
            "required": required,
            **kwargs,
        }

        # Create and validate the property using the model's validation method
        return prop_class.model_validate(property_data)  # type: ignore

    def list(self) -> List[DatasetListItemV2]:
        """
        List all datasets in the app.

        Returns:
            List of dataset items
        """
        path = self._build_app_path("datasets")
        response = self._make_request("GET", path)
        return deserialize_model_list(response, DatasetListItemV2)

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
        if dataset is None:
            # Create from individual parameters
            if name is None:
                raise ValueError("Either dataset object or name parameter must be provided")

            # Convert any dict schema properties to model instances
            schema_props: List[SchemaProperty] = []
            if schema:
                for prop in schema:
                    if isinstance(prop, dict):
                        # Ensure the dict has an ID
                        if "id" not in prop:
                            prop["id"] = cuid_generator()
                        # Create property from dict
                        from autoblocks._impl.datasets_v2.models.schema import create_schema_property

                        schema_props.append(create_schema_property(prop))
                    else:
                        schema_props.append(prop)

            dataset_obj = CreateDatasetV2Request(name=name, description=description, schema=schema_props)
        elif isinstance(dataset, dict):
            # Create from dict
            if "schema" in dataset and isinstance(dataset["schema"], list):
                # Ensure all schema properties have IDs
                for prop in dataset["schema"]:
                    if isinstance(prop, dict) and "id" not in prop:
                        prop["id"] = cuid_generator()

            dataset_obj = CreateDatasetV2Request.model_validate(dataset)
        else:
            # Use the provided model directly
            dataset_obj = dataset

        path = self._build_app_path("datasets")
        response = self._make_request("POST", path, dataset_obj)
        print(f"DEBUG - API Response for dataset creation: {response}")
        return deserialize_model(response, DatasetV2)

    def destroy(self, dataset_id: Optional[str] = None, *, dataset_id_kwarg: Optional[str] = None) -> SuccessResponse:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset external ID (positional argument for backward compatibility)
            dataset_id_kwarg: Dataset external ID (keyword argument)

        Returns:
            Success response
        """
        # Get the dataset ID from either positional or keyword argument
        dataset_id_to_use = dataset_id_kwarg if dataset_id_kwarg is not None else dataset_id
        if dataset_id_to_use is None:
            raise ValueError("dataset_id is required")

        path = self._build_app_path("datasets", dataset_id_to_use)
        response = self._make_request("DELETE", path)
        return deserialize_model(response, SuccessResponse)

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
        # Get the dataset ID from either positional or keyword argument
        dataset_id_to_use = dataset_id_kwarg if dataset_id_kwarg is not None else dataset_id
        if dataset_id_to_use is None:
            raise ValueError("dataset_id is required")

        path = self._build_app_path("datasets", dataset_id_to_use, "items")
        response = self._make_request("GET", path)

        # Handle both response formats:
        # 1. A direct list of items
        # 2. An object with an 'items' field
        if isinstance(response, list):
            return deserialize_model_list(response, DatasetItemV2)
        elif isinstance(response, dict) and "items" in response:
            items = response.get("items", [])
            return deserialize_model_list(items, DatasetItemV2)
        else:
            # Return empty list if no items found
            return []

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
        # Get arguments from either positional or keyword params
        items_to_use = items_kwarg if items_kwarg is not None else items
        dataset_id_to_use = dataset_id_kwarg if dataset_id_kwarg is not None else dataset_id

        if items_to_use is None:
            raise ValueError("items is required")
        if dataset_id_to_use is None:
            raise ValueError("dataset_id is required")

        if isinstance(items_to_use, list):
            # It's a list of items directly
            items_obj = CreateDatasetItemsV2Request(items=items_to_use, splitNames=split_names)
        elif isinstance(items_to_use, dict):
            # It's a dict with items field
            if "items" not in items_to_use and not isinstance(items_to_use.get("items"), list):
                # If it's not a proper items request format, treat it as a single item
                items_obj = CreateDatasetItemsV2Request(items=[items_to_use], splitNames=split_names)
            else:
                # It's already in the correct format
                items_dict = items_to_use.copy()
                if split_names is not None and "splitNames" not in items_dict:
                    items_dict["splitNames"] = split_names
                items_obj = CreateDatasetItemsV2Request.model_validate(items_dict)
        else:
            # It's already a request object
            items_obj = items_to_use

        path = self._build_app_path("datasets", dataset_id_to_use, "items")
        response = self._make_request("POST", path, items_obj)
        return deserialize_model(response, DatasetItemsSuccessResponse)

    def get_schema_by_version(self, *, dataset_id: str, schema_version: int) -> DatasetSchemaV2:
        """
        Get dataset schema by version.

        Args:
            dataset_id: Dataset external ID
            schema_version: Schema version

        Returns:
            Dataset schema
        """
        path = self._build_app_path("datasets", dataset_id, "schema", str(schema_version))
        response = self._make_request("GET", path)
        return deserialize_model(response, DatasetSchemaV2)

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
        params = {}
        if splits:
            params["splits"] = ",".join(splits)

        path = self._build_app_path("datasets", dataset_id, "revisions", revision_id, "items", query_params=params)
        response = self._make_request("GET", path)

        # Handle both response formats
        if isinstance(response, list):
            return deserialize_model_list(response, DatasetItemV2)
        elif isinstance(response, dict) and "items" in response:
            items = response.get("items", [])
            return deserialize_model_list(items, DatasetItemV2)
        else:
            # Return empty list if no items found
            return []

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
        params = {}
        if splits:
            params["splits"] = ",".join(splits)

        path = self._build_app_path("datasets", dataset_id, "schema", str(schema_version), "items", query_params=params)
        response = self._make_request("GET", path)

        # Handle both response formats
        if isinstance(response, list):
            return deserialize_model_list(response, DatasetItemV2)
        elif isinstance(response, dict) and "items" in response:
            items = response.get("items", [])
            return deserialize_model_list(items, DatasetItemV2)
        else:
            # Return empty list if no items found
            return []

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
        # Get arguments from either positional or keyword params
        dataset_id_to_use = dataset_id_kwarg if dataset_id_kwarg is not None else dataset_id
        item_id_to_use = item_id_kwarg if item_id_kwarg is not None else item_id
        data_to_use = data_kwarg if data_kwarg is not None else data

        if dataset_id_to_use is None:
            raise ValueError("dataset_id is required")
        if item_id_to_use is None:
            raise ValueError("item_id is required")
        if data_to_use is None:
            raise ValueError("data is required")

        if isinstance(data_to_use, dict):
            # If it's just data without split_names
            if all(key != "splitNames" for key in data_to_use.keys()):
                update_req = UpdateItemV2Request(data=data_to_use, splitNames=split_names)
            else:
                # It already has the correct structure
                update_dict = data_to_use.copy()
                if split_names is not None and "splitNames" not in update_dict:
                    update_dict["splitNames"] = split_names
                update_req = UpdateItemV2Request.model_validate(update_dict)
        else:
            update_req = data_to_use

        path = self._build_app_path("datasets", dataset_id_to_use, "items", item_id_to_use)
        response = self._make_request("PUT", path, update_req)
        return deserialize_model(response, SuccessResponse)

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
        # Get arguments from either positional or keyword params
        dataset_id_to_use = dataset_id_kwarg if dataset_id_kwarg is not None else dataset_id
        item_id_to_use = item_id_kwarg if item_id_kwarg is not None else item_id

        if dataset_id_to_use is None:
            raise ValueError("dataset_id is required")
        if item_id_to_use is None:
            raise ValueError("item_id is required")

        path = self._build_app_path("datasets", dataset_id_to_use, "items", item_id_to_use)
        response = self._make_request("DELETE", path)
        return deserialize_model(response, SuccessResponse)

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
        if not items:
            return []

        results = []
        for items_batch in batch(items, batch_size):
            request = CreateDatasetItemsV2Request(items=items_batch, splitNames=split_names)
            result = self.create_items(request, dataset_id_kwarg=dataset_id)
            results.append(result)

        return results


def create_datasets_v2_client(api_key: str, app_slug: str, timeout_ms: int = 60000) -> DatasetsV2Client:
    """
    Create a Datasets V2 API client.

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout_ms: Request timeout in milliseconds (default: 60000)

    Returns:
        Datasets V2 API client
    """
    config = {
        "api_key": api_key,
        "app_slug": app_slug,
        "timeout_ms": timeout_ms,
    }
    return DatasetsV2Client(config)
