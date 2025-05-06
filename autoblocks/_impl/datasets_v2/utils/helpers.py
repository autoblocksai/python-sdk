"""Helper utilities for Datasets V2 API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import ParamSpec
from typing import TypeVar
from urllib.parse import urlencode

from autoblocks._impl.datasets_v2.exceptions import ValidationError
from autoblocks._impl.util import encode_uri_component

P = ParamSpec("P")
T = TypeVar("T")


def build_path(*segments: str, query_params: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a URL path with properly encoded segments and optional query parameters.

    Args:
        *segments: Path segments to join
        query_params: Optional query parameters

    Returns:
        Encoded URL path string
    """
    path = "/".join(encode_uri_component(segment) for segment in segments if segment)

    if query_params:
        # Filter out None values
        filtered_params = {k: v for k, v in query_params.items() if v is not None}

        if filtered_params:
            # Handle lists by comma-separating values
            encoded_params = {}
            for key, value in filtered_params.items():
                if isinstance(value, list):
                    encoded_params[key] = ",".join(str(item) for item in value)
                else:
                    encoded_params[key] = str(value)

            query_string = urlencode(encoded_params)
            return f"{path}?{query_string}"

    return path


def validate_required(obj: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that required fields exist in an object.

    Args:
        obj: Dictionary to validate
        required_fields: List of required field names

    Raises:
        ValidationError: If a required field is missing
    """
    missing_fields = [field for field in required_fields if field not in obj]

    if missing_fields:
        missing_str = ", ".join(missing_fields)
        raise ValidationError(f"Missing required fields: {missing_str}")


def batch(items: List[T], batch_size: int) -> List[List[T]]:
    """
    Split a list into batches of specified size.

    Args:
        items: List to split
        batch_size: Size of each batch

    Returns:
        List of batches
    """
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
