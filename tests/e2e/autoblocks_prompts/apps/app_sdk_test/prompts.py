from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

import pydantic

from autoblocks.prompts.v2.context import PromptExecutionContext
from autoblocks.prompts.v2.manager import AutoblocksPromptManager
from autoblocks.prompts.v2.models import FrozenModel
from autoblocks.prompts.v2.renderer import TemplateRenderer
from autoblocks.prompts.v2.renderer import ToolRenderer


class _PromptBasicV2Params(FrozenModel):
    top_k: Union[float, int] = pydantic.Field(..., alias="topK")
    seed: Union[float, int] = pydantic.Field(..., alias="seed")
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicV2TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "first_name": "first_name",
    }

    def template_c(
        self,
        *,
        first_name: str,
    ) -> str:
        return self._render(
            "template-c",
            first_name=first_name,
        )


class _PromptBasicV2ToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicV2ExecutionContext(
    PromptExecutionContext[_PromptBasicV2Params, _PromptBasicV2TemplateRenderer, _PromptBasicV2ToolRenderer]
):
    __params_class__ = _PromptBasicV2Params
    __template_renderer_class__ = _PromptBasicV2TemplateRenderer
    __tool_renderer_class__ = _PromptBasicV2ToolRenderer


class _PromptBasicV2PromptManager(AutoblocksPromptManager[_PromptBasicV2ExecutionContext]):
    __app_id__ = "jqg74mpzzovssq38j055yien"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "2"
    __execution_context_class__ = _PromptBasicV2ExecutionContext


class _PromptBasicV1Params(FrozenModel):
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    stop_sequences: list[str] = pydantic.Field(..., alias="stopSequences")
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicV1TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "weather": "weather",
    }

    def template_a(
        self,
        *,
        name: str,
        weather: str,
    ) -> str:
        return self._render(
            "template-a",
            name=name,
            weather=weather,
        )

    def template_b(
        self,
        *,
        name: str,
    ) -> str:
        return self._render(
            "template-b",
            name=name,
        )


class _PromptBasicV1ToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicV1ExecutionContext(
    PromptExecutionContext[_PromptBasicV1Params, _PromptBasicV1TemplateRenderer, _PromptBasicV1ToolRenderer]
):
    __params_class__ = _PromptBasicV1Params
    __template_renderer_class__ = _PromptBasicV1TemplateRenderer
    __tool_renderer_class__ = _PromptBasicV1ToolRenderer


class _PromptBasicV1PromptManager(AutoblocksPromptManager[_PromptBasicV1ExecutionContext]):
    __app_id__ = "jqg74mpzzovssq38j055yien"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "1"
    __execution_context_class__ = _PromptBasicV1ExecutionContext


class PromptBasicFactory:
    @staticmethod
    def create(
        major_version: Optional[str] = None,
        minor_version: str = "0",
        api_key: Optional[str] = None,
        init_timeout: Optional[float] = None,
        refresh_timeout: Optional[float] = None,
        refresh_interval: Optional[float] = None,
    ) -> Union[_PromptBasicV1PromptManager, _PromptBasicV2PromptManager]:
        kwargs: Dict[str, Any] = {}
        if api_key is not None:
            kwargs["api_key"] = api_key
        if init_timeout is not None:
            kwargs["init_timeout"] = init_timeout
        if refresh_timeout is not None:
            kwargs["refresh_timeout"] = refresh_timeout
        if refresh_interval is not None:
            kwargs["refresh_interval"] = refresh_interval

        if major_version is None:
            major_version = "2"  # Latest version

        if major_version == "1":
            return _PromptBasicV1PromptManager(minor_version=minor_version, **kwargs)
        if major_version == "2":
            return _PromptBasicV2PromptManager(minor_version=minor_version, **kwargs)

        raise ValueError("Unsupported major version. Available versions: 1, 2")
