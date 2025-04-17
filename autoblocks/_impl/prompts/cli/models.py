from typing import Optional

from autoblocks._impl.prompts.models import AutogeneratePromptsConfig
from autoblocks._impl.prompts.models import FrozenModel


class AutogenerateConfig(FrozenModel):
    """Configuration for autogenerating V1 prompts."""

    prompts: AutogeneratePromptsConfig


class YamlConfig(FrozenModel):
    """
    Configuration for the Autoblocks CLI.

    The structure supports:
    - 'autogenerate' - Legacy V1 prompts config (unchanged)
    """

    # Legacy V1 configuration
    autogenerate: Optional[AutogenerateConfig] = None
