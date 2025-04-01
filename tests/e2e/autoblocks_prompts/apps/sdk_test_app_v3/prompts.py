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


class _PromptBasicUndeployedParams(FrozenModel):
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicUndeployedTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def test_do_not_deploy(
        self,
    ) -> str:
        return self._render(
            "test-do-not-deploy",
        )


class _PromptBasicUndeployedToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _PromptBasicUndeployedExecutionContext(
    PromptExecutionContext[
        _PromptBasicUndeployedParams, _PromptBasicUndeployedTemplateRenderer, _PromptBasicUndeployedToolRenderer
    ]
):
    __params_class__ = _PromptBasicUndeployedParams
    __template_renderer_class__ = _PromptBasicUndeployedTemplateRenderer
    __tool_renderer_class__ = _PromptBasicUndeployedToolRenderer


class _PromptBasicUndeployedPromptManager(AutoblocksPromptManager[_PromptBasicUndeployedExecutionContext]):
    __app_id__ = "b108cei22gakuuujcbtnrt2a"
    __prompt_id__ = "prompt-basic"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = _PromptBasicUndeployedExecutionContext


class PromptBasicFactory:
    @staticmethod
    def create(
        major_version: str = "undeployed",
        minor_version: str = "latest",
        api_key: Optional[str] = None,
        init_timeout: Optional[float] = None,
        refresh_timeout: Optional[float] = None,
        refresh_interval: Optional[float] = None,
    ) -> _PromptBasicUndeployedPromptManager:
        kwargs: Dict[str, Any] = {}
        if api_key is not None:
            kwargs["api_key"] = api_key
        if init_timeout is not None:
            kwargs["init_timeout"] = init_timeout
        if refresh_timeout is not None:
            kwargs["refresh_timeout"] = refresh_timeout
        if refresh_interval is not None:
            kwargs["refresh_interval"] = refresh_interval

        # Prompt has no deployed versions
        if major_version != "undeployed":
            raise ValueError("Unsupported major version. This prompt has no deployed versions.")
        return _PromptBasicUndeployedPromptManager(minor_version=minor_version, **kwargs)
