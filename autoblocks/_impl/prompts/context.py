import abc
import functools
from typing import Any
from typing import Dict
from typing import Generic
from typing import Type
from typing import TypeVar

import pydantic

from autoblocks._impl.prompts.models import HeadlessPrompt
from autoblocks._impl.prompts.renderer import TemplateRenderer

ParamsType = TypeVar("ParamsType", bound=pydantic.BaseModel)
TemplateRendererType = TypeVar("TemplateRendererType", bound=TemplateRenderer)


class PromptExecutionContext(abc.ABC, Generic[ParamsType, TemplateRendererType]):
    __params_class__: Type[ParamsType]
    __template_renderer_class__: Type[TemplateRendererType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in (
            "__params_class__",
            "__template_renderer_class__",
        ):
            if not hasattr(cls, attr):
                raise ValueError(f"PromptExecutionContext subclass {cls} must define {attr}")

    def __init__(self, prompt: HeadlessPrompt) -> None:
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
        return self.__template_renderer_class__(
            self._prompt,
        )

    @functools.lru_cache(1)
    def track(self) -> Dict[str, Any]:
        prompt = self._prompt.model_dump()
        prompt.pop("params", None)
        return prompt
