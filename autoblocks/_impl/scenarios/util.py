from typing import List

from autoblocks._impl.util import parse_autoblocks_overrides


def get_selected_scenario_ids() -> List[str]:
    """
    Gets the list of selected scenario IDs from overrides.
    Returns empty list if no scenarios are selected or not in testing context.
    """
    overrides = parse_autoblocks_overrides()
    return overrides.test_selected_scenarios_ids
