import re
from typing import Any
from typing import Optional


def normalize_app_name(app_name: str) -> str:
    """
    Convert app name to a valid Python identifier.

    Args:
        app_name: The original app name

    Returns:
        A normalized name suitable for use as a Python identifier

    Examples:
        "My App" -> "my_app"
        "Test-ApP" -> "test_app"
        "123 Service" -> "app_123_service"
    """
    # Replace non-alphanumeric chars with underscores
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", app_name)

    # Ensure it starts with a letter
    if not normalized[0].isalpha():
        normalized = "app_" + normalized

    # Make it lowercase for consistency
    return normalized.lower()


def to_snake_case(s: str) -> str:
    """
    Convert a string to snake_case.

    Args:
        s: The string to convert

    Returns:
        The snake_case version of the string
    """
    # Remove leading numbers
    s = re.sub(r"^\d+", "", s)

    # Replace all non-alphanumeric characters with spaces
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s)

    # Replace spaces with underscores
    s = re.sub(r"\s+", "_", s)

    # Add underscores between camel case words
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)

    # Remove leading and trailing underscores
    s = s.strip("_")

    return s.lower()


def to_title_case(s: str) -> str:
    """
    Convert a string to TitleCase.

    Args:
        s: The string to convert

    Returns:
        The TitleCase version of the string
    """
    # Remove leading numbers
    s = re.sub(r"^\d+", "", s)

    # Replace all non-alphanumeric characters with underscores
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)

    # Replace all underscores with capital letter of next word
    return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), s)


def infer_type(value: Any) -> Optional[str]:
    """
    Infer the Python type of a value for code generation.

    Args:
        value: The value to infer the type of

    Returns:
        A string representation of the type, or None if the type can't be inferred
    """
    if isinstance(value, str):
        return "str"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, (int, float)):
        # The default union mode in pydantic is "smart" mode,
        # which will use the most specific type possible.
        return "Union[float, int]"
    elif isinstance(value, list):
        if not value:
            return "List[Any]"  # Empty list should have a type parameter

        # Check if all items have the same type
        first_type = type(value[0])
        if all(isinstance(item, first_type) for item in value):
            element_type = infer_type(value[0])
            if element_type:
                return f"List[{element_type}]"

        # Mixed types or unknown
        return "List[Any]"
    elif isinstance(value, dict):
        return "Dict[str, Any]"
    return None


def indent(times: int = 1, size: int = 4) -> str:
    """
    Create an indentation string.

    Args:
        times: Number of indentation levels
        size: Size of each indentation level in spaces

    Returns:
        A string with the specified indentation
    """
    return " " * size * times
