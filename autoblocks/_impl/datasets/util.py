from typing import List

from autoblocks._impl.util import parse_autoblocks_overrides


def get_selected_datasets() -> List[str]:
    """
    Gets the list of selected dataset external IDs from overrides.
    Returns empty list if no datasets are selected or not in testing context.
    """
    overrides = parse_autoblocks_overrides()
    return overrides.test_selected_datasets
