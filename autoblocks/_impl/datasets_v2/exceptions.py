"""Custom exceptions for Datasets V2 API."""

from typing import Any
from typing import Dict
from typing import Optional

import httpx


class AutoblocksError(Exception):
    """Base class for all Autoblocks exceptions."""

    pass


class ValidationError(AutoblocksError):
    """Raised when a validation error occurs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class APIError(AutoblocksError):
    """Raised when an API error occurs."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response: Optional[httpx.Response] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.response = response
        self.details = details or {}
        super().__init__(f"HTTP {status_code}: {message}")


class ConfigurationError(AutoblocksError):
    """Raised when there is a configuration error."""

    pass


class ResourceNotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: str, response: Optional[httpx.Response] = None):
        super().__init__(404, f"{resource_type} not found: {resource_id}", response)
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", response: Optional[httpx.Response] = None):
        super().__init__(401, message, response)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", response: Optional[httpx.Response] = None):
        super().__init__(429, message, response)
