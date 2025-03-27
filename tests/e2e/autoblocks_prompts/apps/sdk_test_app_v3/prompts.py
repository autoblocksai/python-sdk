from typing import Any
from typing import Dict
from typing import Optional

import pydantic

from autoblocks.prompts.v2.context import PromptExecutionContext
from autoblocks.prompts.v2.manager import AutoblocksPromptManager
from autoblocks.prompts.v2.models import FrozenModel
from autoblocks.prompts.v2.renderer import TemplateRenderer
from autoblocks.prompts.v2.renderer import ToolRenderer


class _DoNotDeployUndeployedParams(FrozenModel):
    pass


class _DoNotDeployUndeployedTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def test_do_not_deploy(
        self,
    ) -> str:
        return self._render(
            "test-do-not-deploy",
        )


class _DoNotDeployUndeployedToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class _DoNotDeployUndeployedExecutionContext(
    PromptExecutionContext[
        _DoNotDeployUndeployedParams, _DoNotDeployUndeployedTemplateRenderer, _DoNotDeployUndeployedToolRenderer
    ]
):
    __params_class__ = _DoNotDeployUndeployedParams
    __template_renderer_class__ = _DoNotDeployUndeployedTemplateRenderer
    __tool_renderer_class__ = _DoNotDeployUndeployedToolRenderer


class _DoNotDeployUndeployedPromptManager(AutoblocksPromptManager[_DoNotDeployUndeployedExecutionContext]):
    __app_id__ = "h12a6fsmomuar1ww4fuxbjgl"
    __prompt_id__ = "do-not-deploy"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = _DoNotDeployUndeployedExecutionContext


class DoNotDeployFactory:
    @staticmethod
    def create(
        major_version: str = "undeployed",
        minor_version: str = "latest",
        api_key: Optional[str] = None,
        init_timeout: Optional[float] = None,
        refresh_timeout: Optional[float] = None,
        refresh_interval: Optional[float] = None,
    ) -> _DoNotDeployUndeployedPromptManager:
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
        return _DoNotDeployUndeployedPromptManager(minor_version=minor_version, **kwargs)


class _PromptBasicV1Params(FrozenModel):
    model: str = pydantic.Field(..., alias="model")


class _PromptBasicV1TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def test(
        self,
    ) -> str:
        return self._render(
            "test",
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
    __app_id__ = "h12a6fsmomuar1ww4fuxbjgl"
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
    ) -> _PromptBasicV1PromptManager:
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
            major_version = "1"  # Latest version

        if major_version == "1":
            return _PromptBasicV1PromptManager(minor_version=minor_version, **kwargs)

        raise ValueError("Unsupported major version. Available versions: 1")
