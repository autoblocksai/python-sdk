import abc
import functools
from typing import Any, Dict, Generic, Type, TypeVar

import pydantic

from autoblocks._impl.api.v2.models import Prompt, PromptMajorVersion
from autoblocks._impl.prompts.renderer import TemplateRenderer
from autoblocks._impl.prompts.renderer import ToolRenderer

ParamsType = TypeVar("ParamsType", bound=pydantic.BaseModel)
TemplateRendererType = TypeVar("TemplateRendererType", bound=TemplateRenderer)
ToolRendererType = TypeVar("ToolRendererType", bound=ToolRenderer)


class PromptExecutionContext(abc.ABC, Generic[ParamsType, TemplateRendererType, ToolRendererType]):
    """Execution context for a prompt in the V2 API.
    
    This provides access to the prompt's parameters, templates, and tools.
    """
    __params_class__: Type[ParamsType]
    __template_renderer_class__: Type[TemplateRendererType]
    __tool_renderer_class__: Type[ToolRendererType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("__params_class__", "__template_renderer_class__", "__tool_renderer_class__"):
            if not hasattr(cls, attr):
                raise ValueError(f"PromptExecutionContext subclass {cls} must define {attr}")

    def __init__(self, prompt: Prompt, major_version: PromptMajorVersion) -> None:
        """Initialize the execution context.
        
        Args:
            prompt: The prompt to use.
            major_version: The major version of the prompt to use.
        """
        self._prompt = prompt
        self._major_version = major_version

    @functools.cached_property
    def params(self) -> ParamsType:
        """Get the parameters for this prompt."""
        if self._major_version.params:
            params = self._major_version.params
        else:
            params = {}
        return self.__params_class__(
            **params,
        )

    @functools.cached_property
    def render_template(self) -> TemplateRendererType:
        """Get the template renderer for this prompt."""
        return self.__template_renderer_class__(
            self._major_version.templates,
        )

    @functools.cached_property
    def render_tool(self) -> ToolRendererType:
        """Get the tool renderer for this prompt."""
        return self.__tool_renderer_class__(
            self._major_version.tools_params or [],
        )

    def track(self) -> Dict[str, Any]:
        """Get tracking information for this prompt."""
        return {
            "id": self._prompt.id,
            "appId": self._prompt.app_id,
            "majorVersion": self._major_version.major_version,
            # Additional tracking information
        } 