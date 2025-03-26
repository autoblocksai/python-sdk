import re
from typing import Any
from typing import Optional


def to_title_case(s: str) -> str:
    # Remove leading numbers
    s = re.sub(r"^\d+", "", s)
    # Replace all non-alphanumeric characters with underscores
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    # Replace all underscores with capital letter of next word
    return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), s)


def to_snake_case(s: str) -> str:
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


def infer_type(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return "str"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, (int, float)):
        # The default union mode in pydantic is "smart" mode,
        # which will use the most specific type possible.
        # https://docs.pydantic.dev/latest/concepts/unions/
        return "Union[float, int]"
    elif isinstance(value, list):
        if len(value) > 0:
            return f"list[{infer_type(value[0])}]"
    elif isinstance(value, dict):
        return "Dict[str, Any]"
    return None


def indent(times: int = 1, size: int = 4) -> str:
    return " " * size * times


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
