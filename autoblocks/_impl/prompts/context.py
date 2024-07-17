import abc
import functools
from typing import Any
from typing import Dict
from typing import Generic
from typing import Type
from typing import TypeVar

import pydantic

from autoblocks._impl.prompts.models import Prompt
from autoblocks._impl.prompts.renderer import TemplateRenderer
from autoblocks._impl.prompts.renderer import ToolRenderer

ParamsType = TypeVar("ParamsType", bound=pydantic.BaseModel)
TemplateRendererType = TypeVar("TemplateRendererType", bound=TemplateRenderer)
ToolRendererType = TypeVar("ToolRendererType", bound=ToolRenderer)


class PromptExecutionContext(abc.ABC, Generic[ParamsType, TemplateRendererType, ToolRendererType]):
    __params_class__: Type[ParamsType]
    __template_renderer_class__: Type[TemplateRendererType]
    __tool_renderer_class__: Type[ToolRendererType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("__params_class__", "__template_renderer_class__", "__tool_renderer_class__"):
            if not hasattr(cls, attr):
                raise ValueError(f"PromptExecutionContext subclass {cls} must define {attr}")

    def __init__(self, prompt: Prompt) -> None:
        self._prompt = prompt

    @functools.cached_property
    def params(self) -> ParamsType:
        if self._prompt.params:
            params = self._prompt.params.params or {}
        else:
            params = {}
        return self.__params_class__(
            **params,
        )

    @functools.cached_property
    def render(self) -> TemplateRendererType:
        """
        @deprecated use `render_template` instead
        """
        return self.__template_renderer_class__(
            self._prompt,
        )

    @functools.cached_property
    def render_template(self) -> TemplateRendererType:
        return self.__template_renderer_class__(
            self._prompt,
        )

    @functools.cached_property
    def render_tool(self) -> ToolRendererType:
        return self.__tool_renderer_class__(
            self._prompt,
        )

    def track(self) -> Dict[str, Any]:
        return self._prompt.tracking
