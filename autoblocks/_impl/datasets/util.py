from typing import Any
from typing import Dict
from typing import List

from autoblocks._impl.api.exceptions import ValidationError
from autoblocks._impl.util import parse_autoblocks_overrides


def get_selected_datasets() -> List[str]:
    """
    Gets the list of selected dataset external IDs from overrides.
    Returns empty list if no datasets are selected or not in testing context.
    """
    overrides = parse_autoblocks_overrides()
    return overrides.test_selected_datasets


def validate_unique_property_names(schema: List[Dict[str, Any]]) -> None:
    """
    Validate that all property names in schema are unique.

    Args:
        schema: List of property dictionaries

    Raises:
        ValidationError: If duplicate property names are found
    """
    property_names = [prop.get("name") for prop in schema]
    if len(property_names) != len(set(property_names)):
        raise ValidationError("Schema property names must be unique")
