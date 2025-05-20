import abc
import json
import logging
from datetime import timedelta
from typing import Any
from typing import Optional

import httpx

from autoblocks._impl.api.exceptions import APIError
from autoblocks._impl.api.exceptions import ValidationError
from autoblocks._impl.api.exceptions import parse_error_response
from autoblocks._impl.api.utils.helpers import build_path
from autoblocks._impl.api.utils.serialization import serialize_model
from autoblocks._impl.config.constants import API_ENDPOINT_V2

log = logging.getLogger(__name__)


class BaseAppResourceClient(abc.ABC):
    """Base class for all app resource api clients."""

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
