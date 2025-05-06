"""Helper utilities for Datasets V2 API."""
import functools
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, ParamSpec, cast
from urllib.parse import urlencode

from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.datasets_v2.exceptions import ValidationError

P = ParamSpec('P')
T = TypeVar('T')


def build_path(*segments: str, query_params: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a URL path with properly encoded segments and optional query parameters.
    
    Args:
        *segments: Path segments to join
        query_params: Optional query parameters
        
    Returns:
        Encoded URL path string
    """
    path = '/'.join(encode_uri_component(segment) for segment in segments if segment)
    
    if query_params:
        # Filter out None values
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        
        if filtered_params:
            # Handle lists by comma-separating values
            encoded_params = {}
            for key, value in filtered_params.items():
                if isinstance(value, list):
                    encoded_params[key] = ','.join(str(item) for item in value)
                else:
                    encoded_params[key] = str(value)
            
            query_string = urlencode(encoded_params)
            return f"{path}?{query_string}"
    
    return path


def retry(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    retry_on_exceptions: tuple = (ConnectionError, TimeoutError)
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff factor for exponential delay
        retry_on_exceptions: Tuple of exceptions to retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** attempt)
                        time.sleep(sleep_time)
                    else:
                        raise last_exception
            
            # This should never happen, but keeps type checkers happy
            raise last_exception or RuntimeError("Unexpected error in retry logic")
            
        return wrapper
    return decorator


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
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)] 