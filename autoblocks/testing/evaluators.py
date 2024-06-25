from autoblocks._impl.testing.evaluators.battle import BaseAutomaticBattle
from autoblocks._impl.testing.evaluators.battle import BaseAutomaticBattle as AutomaticBattle
from autoblocks._impl.testing.evaluators.battle import BaseManualBattle
from autoblocks._impl.testing.evaluators.battle import BaseManualBattle as ManualBattle
from autoblocks._impl.testing.evaluators.has_all_substrings import BaseHasAllSubstrings
from autoblocks._impl.testing.evaluators.has_all_substrings import BaseHasAllSubstrings as HasAllSubstrings

__all__ = [
    "BaseHasAllSubstrings",
    "BaseAutomaticBattle",
    "BaseManualBattle",
    # deprecated
    "HasAllSubstrings",
    "AutomaticBattle",
    "ManualBattle",
]
