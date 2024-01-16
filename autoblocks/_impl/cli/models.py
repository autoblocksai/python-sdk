import pydantic

from autoblocks._impl.prompts.models import AutogeneratePromptsConfig


class FrozenModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)


class AutogenerateConfig(FrozenModel):
    prompts: AutogeneratePromptsConfig


class YamlConfig(FrozenModel):
    autogenerate: AutogenerateConfig
