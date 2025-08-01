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


class _PromptBasicV4Params(FrozenModel):
    max_completion_tokens: Union[float, int] = pydantic.Field(
        ...,
        alias="maxCompletionTokens",
    )
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicV4TemplateRenderer(TemplateRenderer):
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


class _PromptBasicV4ToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicV4ExecutionContext(
    PromptExecutionContext[_PromptBasicV4Params, _PromptBasicV4TemplateRenderer, _PromptBasicV4ToolRenderer]
):
    __params_class__ = _PromptBasicV4Params
    __template_renderer_class__ = _PromptBasicV4TemplateRenderer
    __tool_renderer_class__ = _PromptBasicV4ToolRenderer


class _PromptBasicV4PromptManager(AutoblocksPromptManager[_PromptBasicV4ExecutionContext]):
    __app_id__ = "b5sz3k5d61w9f8325fhxuxkr"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "4"
    __execution_context_class__ = _PromptBasicV4ExecutionContext


class _PromptBasicV3Params(FrozenModel):
    max_completion_tokens: Union[float, int] = pydantic.Field(
        ...,
        alias="maxCompletionTokens",
    )
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicV3TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def template_c(
        self,
    ) -> str:
        return self._render(
            "template-c",
        )


class _PromptBasicV3ToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicV3ExecutionContext(
    PromptExecutionContext[_PromptBasicV3Params, _PromptBasicV3TemplateRenderer, _PromptBasicV3ToolRenderer]
):
    __params_class__ = _PromptBasicV3Params
    __template_renderer_class__ = _PromptBasicV3TemplateRenderer
    __tool_renderer_class__ = _PromptBasicV3ToolRenderer


class _PromptBasicV3PromptManager(AutoblocksPromptManager[_PromptBasicV3ExecutionContext]):
    __app_id__ = "b5sz3k5d61w9f8325fhxuxkr"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "3"
    __execution_context_class__ = _PromptBasicV3ExecutionContext


class _PromptBasicV2Params(FrozenModel):
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
    __app_id__ = "b5sz3k5d61w9f8325fhxuxkr"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "2"
    __execution_context_class__ = _PromptBasicV2ExecutionContext


class _PromptBasicV1Params(FrozenModel):
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


class _PromptBasicV1ToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicV1ExecutionContext(
    PromptExecutionContext[_PromptBasicV1Params, _PromptBasicV1TemplateRenderer, _PromptBasicV1ToolRenderer]
):
    __params_class__ = _PromptBasicV1Params
    __template_renderer_class__ = _PromptBasicV1TemplateRenderer
    __tool_renderer_class__ = _PromptBasicV1ToolRenderer


class _PromptBasicV1PromptManager(AutoblocksPromptManager[_PromptBasicV1ExecutionContext]):
    __app_id__ = "b5sz3k5d61w9f8325fhxuxkr"
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
    ) -> Union[
        _PromptBasicV1PromptManager,
        _PromptBasicV2PromptManager,
        _PromptBasicV3PromptManager,
        _PromptBasicV4PromptManager,
    ]:
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
            major_version = "4"  # Latest version

        if major_version == "1":
            return _PromptBasicV1PromptManager(minor_version=minor_version, **kwargs)
        if major_version == "2":
            return _PromptBasicV2PromptManager(minor_version=minor_version, **kwargs)
        if major_version == "3":
            return _PromptBasicV3PromptManager(minor_version=minor_version, **kwargs)
        if major_version == "4":
            return _PromptBasicV4PromptManager(minor_version=minor_version, **kwargs)

        raise ValueError("Unsupported major version. Available versions: 1, 2, 3, 4")
