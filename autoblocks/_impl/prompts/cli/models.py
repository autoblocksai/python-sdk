from typing import Dict, List, Optional, Any

from pydantic import Field, model_validator

from autoblocks._impl.prompts.models import AutogeneratePromptsConfig, FrozenModel

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
