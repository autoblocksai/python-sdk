from typing import Dict, List, Optional, Any

from pydantic import Field, model_validator

from autoblocks._impl.prompts.models import AutogeneratePromptsConfig, FrozenModel
from autoblocks._impl.prompts.v2.models import AutogeneratePromptsConfig as V2AutogeneratePromptsConfig
from autoblocks._impl.prompts.v2.models import AutogeneratePromptConfig as V2PromptConfig


class AutogenerateConfig(FrozenModel):
    """Configuration for autogenerating V1 prompts."""
    prompts: AutogeneratePromptsConfig


# V2 app configuration
class V2AppConfig(FrozenModel):
    """Configuration for a single V2 app."""
    app_id: str
    outfile: Optional[str] = None
    prompts: List[V2PromptConfig]


# V2 configuration with multiple apps
class V2PromptsConfig(FrozenModel):
    """Configuration for V2 prompts with multiple apps."""
    outfile: Optional[str] = None  # Default outfile if not specified per app
    app_id: Optional[str] = None  # For backward compatibility
    prompts: Optional[List[V2PromptConfig]] = None  # For backward compatibility
    apps: Optional[List[V2AppConfig]] = None

    @model_validator(mode='after')
    def validate_config(self):
        """Validate configuration structure."""
        # If both single app and multiple apps config provided, ensure one is used
        if self.prompts and self.apps:
            raise ValueError("Cannot specify both 'prompts' and 'apps' in V2 configuration")
        
        # Ensure app_id is provided if prompts is provided (single app case)
        if self.prompts and not self.app_id:
            raise ValueError("Must specify 'app_id' when using 'prompts' in V2 configuration")
        
        # Ensure outfile is provided somewhere
        if not self.outfile and self.apps:
            # Check if all apps have outfiles
            missing_outfiles = [app.app_id for app in self.apps if not app.outfile]
            if missing_outfiles:
                raise ValueError(
                    f"The following apps are missing 'outfile' and no default outfile is specified: {', '.join(missing_outfiles)}"
                )
        
        return self


class V2AutogenerateConfig(FrozenModel):
    """Configuration for autogenerating V2 prompts."""
    prompts: V2PromptsConfig


class YamlConfig(FrozenModel):
    """
    Configuration for the Autoblocks CLI.
    
    The structure supports:
    - 'autogenerate' - Legacy V1 prompts config (unchanged)
    - 'autogenerate_v2' - V2 prompts config with multiple apps support
    """
    # Legacy V1 configuration
    autogenerate: Optional[AutogenerateConfig] = None
    
    # V2 configuration with multiple apps support
    autogenerate_v2: Optional[V2AutogenerateConfig] = None
    
    def get_v2_configs(self) -> Dict[str, V2AutogeneratePromptsConfig]:
        """
        Get all V2 app configurations from this config.
        
        Returns:
            Dictionary mapping section names to V2 prompt configurations
        """
        configs = {}
        
        if not self.autogenerate_v2 or not self.autogenerate_v2.prompts:
            return configs
        
        v2_prompts = self.autogenerate_v2.prompts
        
        # Handle single-app case (backward compatibility)
        if v2_prompts.app_id and v2_prompts.prompts:
            # Convert to V2AutogeneratePromptsConfig
            v2_config = V2AutogeneratePromptsConfig(
                outfile=v2_prompts.outfile or "prompts_v2.py",
                app_id=v2_prompts.app_id,
                prompts=v2_prompts.prompts
            )
            
            configs["autogenerate_v2"] = v2_config
        
        # Handle multi-app case
        if v2_prompts.apps:
            for app in v2_prompts.apps:
                # Use app-specific outfile or default
                outfile = app.outfile or v2_prompts.outfile
                if not outfile:
                    outfile = f"{app.app_id}_prompts.py"
                
                # Convert to V2AutogeneratePromptsConfig
                v2_config = V2AutogeneratePromptsConfig(
                    outfile=outfile,
                    app_id=app.app_id,
                    prompts=app.prompts
                )
                
                # Use app_id as section name
                section_name = f"app_{app.app_id}"
                configs[section_name] = v2_config
        
        return configs
