"""Helper functions for dataset operations."""

import urllib.parse
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional

from autoblocks._impl.datasets.exceptions import ValidationError


def build_path(*parts: str, query_params: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a URL path from parts and query parameters.

    Args:
        *parts: Path parts to join
        query_params: Optional query parameters

    Returns:
        Built path with encoded query parameters if any
    """
    # URL encode each path part
    path = "/".join(urllib.parse.quote(part.strip("/")) for part in parts if part)

    # Add query parameters if provided
    if query_params:
        # Filter out None values
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        if filtered_params:
            query_string = "&".join(
                f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}" for k, v in filtered_params.items()
            )
            path = f"{path}?{query_string}"

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


def batch(items: List[Any], batch_size: int) -> Generator[List[Any], None, None]:
    """
    Split a list into batches of a specified size.

    Args:
        items: List to batch
        batch_size: Size of each batch

    Yields:
        Batches of items
    """
    if batch_size <= 0:
        raise ValidationError("Batch size must be a positive integer")

    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]
