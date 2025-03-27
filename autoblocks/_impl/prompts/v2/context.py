import abc
import functools
from typing import Any
from typing import Dict
from typing import Generic
from typing import Type
from typing import TypeVar

import pydantic

from autoblocks._impl.prompts.v2.renderer import TemplateRenderer
from autoblocks._impl.prompts.v2.renderer import ToolRenderer

ParamsType = TypeVar("ParamsType", bound=pydantic.BaseModel)
TemplateRendererType = TypeVar("TemplateRendererType", bound=TemplateRenderer)
ToolRendererType = TypeVar("ToolRendererType", bound=ToolRenderer)


class PromptExecutionContext(abc.ABC, Generic[ParamsType, TemplateRendererType, ToolRendererType]):
    """
    Context for executing a prompt in V2.
    This manages access to parameters, template rendering, and tool rendering.
    """

    __params_class__: Type[ParamsType]
    __template_renderer_class__: Type[TemplateRendererType]
    __tool_renderer_class__: Type[ToolRendererType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("__params_class__", "__template_renderer_class__", "__tool_renderer_class__"):
            if not hasattr(cls, attr):
                raise ValueError(f"PromptExecutionContext subclass {cls} must define {attr}")

    def __init__(self, prompt_data: Dict[str, Any]) -> None:
        """
        Initialize the context with prompt data.

        Args:
            prompt_data: The prompt data from the API
        """
        self._prompt_data = prompt_data

    @functools.cached_property
    def params(self) -> ParamsType:
        """Get the typed parameters for this prompt."""
        if params_data := self._prompt_data.get("params", {}):
            params = params_data.get("params", {})
        else:
            params = {}
        return self.__params_class__(**params)

    @functools.cached_property
    def render_template(self) -> TemplateRendererType:
        """Get the template renderer for this prompt."""
        # Create a map of template_id -> template_string
        templates = {}
        for template in self._prompt_data.get("templates", []):
            templates[template["id"]] = template["template"]

        return self.__template_renderer_class__(templates)

    @functools.cached_property
    def render_tool(self) -> ToolRendererType:
        """Get the tool renderer for this prompt."""
        # Create a map of tool_name -> tool_data
        tools = {}
        for tool in self._prompt_data.get("tools", []):
            tools[tool["name"]] = tool

        return self.__tool_renderer_class__(tools)

    def track(self) -> Dict[str, Any]:
        """Get tracking data for this prompt execution."""
        return self._prompt_data
