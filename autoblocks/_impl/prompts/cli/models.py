from autoblocks._impl.prompts.models import AutogeneratePromptsConfig
from autoblocks._impl.prompts.models import FrozenModel


class AutogenerateConfig(FrozenModel):
    prompts: AutogeneratePromptsConfig


class YamlConfig(FrozenModel):
    autogenerate: AutogenerateConfig
