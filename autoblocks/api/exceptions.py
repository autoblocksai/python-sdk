"""Exception classes for the Autoblocks API."""

from autoblocks._impl.api.exceptions import APIError
from autoblocks._impl.api.exceptions import AuthenticationError
from autoblocks._impl.api.exceptions import AutoblocksError
from autoblocks._impl.api.exceptions import RateLimitError
from autoblocks._impl.api.exceptions import ResourceNotFoundError
from autoblocks._impl.api.exceptions import ValidationError

__all__ = [
    "APIError",
    "AuthenticationError",
    "AutoblocksError",
    "RateLimitError",
    "ResourceNotFoundError",
    "ValidationError",
]
