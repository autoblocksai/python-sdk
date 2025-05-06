"""Exception classes for the Datasets API."""

from autoblocks._impl.datasets.exceptions import APIError
from autoblocks._impl.datasets.exceptions import AuthenticationError
from autoblocks._impl.datasets.exceptions import AutoblocksError
from autoblocks._impl.datasets.exceptions import ConfigurationError
from autoblocks._impl.datasets.exceptions import RateLimitError
from autoblocks._impl.datasets.exceptions import ResourceNotFoundError
from autoblocks._impl.datasets.exceptions import ValidationError

__all__ = [
    "APIError",
    "AuthenticationError",
    "AutoblocksError",
    "ConfigurationError",
    "RateLimitError",
    "ResourceNotFoundError",
    "ValidationError",
]
