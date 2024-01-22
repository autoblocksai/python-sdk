############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from enum import Enum
from typing import List  # noqa: F401

import pydantic

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer


class UsedByCiDontDeleteParams(FrozenModel):
    top_p: float = pydantic.Field(..., alias="topP")
    model: str = pydantic.Field(..., alias="model")
    max_tokens: float = pydantic.Field(..., alias="maxTokens")
    temperature: float = pydantic.Field(..., alias="temperature")
    presence_penalty: float = pydantic.Field(..., alias="presencePenalty")
    frequency_penalty: float = pydantic.Field(..., alias="frequencyPenalty")


class UsedByCiDontDeleteTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "optional?": "optional",
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
        optional: str,
    ) -> str:
        return self._render(
            "template-b",
            name=name,
            optional=optional,
        )

    def template_c(
        self,
    ) -> str:
        return self._render(
            "template-c",
        )


class UsedByCiDontDeleteExecutionContext(
    PromptExecutionContext[
        UsedByCiDontDeleteParams,
        UsedByCiDontDeleteTemplateRenderer,
    ],
):
    __params_class__ = UsedByCiDontDeleteParams
    __template_renderer_class__ = UsedByCiDontDeleteTemplateRenderer


class UsedByCiDontDeleteMinorVersion(Enum):
    v0 = "0"
    v1 = "1"
    v2 = "2"
    v3 = "3"
    LATEST = "latest"


class UsedByCiDontDeletePromptManager(
    AutoblocksPromptManager[
        UsedByCiDontDeleteExecutionContext,
        UsedByCiDontDeleteMinorVersion,
    ],
):
    __prompt_id__ = "used-by-ci-dont-delete"
    __prompt_major_version__ = "2"
    __execution_context_class__ = UsedByCiDontDeleteExecutionContext


class UsedByCiDontDeleteNoParamsTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
    }

    def my_template_id(
        self,
        *,
        name: str,
    ) -> str:
        return self._render(
            "my-template-id",
            name=name,
        )


class UsedByCiDontDeleteNoParamsExecutionContext(
    PromptExecutionContext[
        None,
        UsedByCiDontDeleteNoParamsTemplateRenderer,
    ],
):
    __params_class__ = None
    __template_renderer_class__ = UsedByCiDontDeleteNoParamsTemplateRenderer

    @property
    def params(self) -> None:
        return None


class UsedByCiDontDeleteNoParamsMinorVersion(Enum):
    v0 = "0"
    LATEST = "latest"


class UsedByCiDontDeleteNoParamsPromptManager(
    AutoblocksPromptManager[
        UsedByCiDontDeleteNoParamsExecutionContext,
        UsedByCiDontDeleteNoParamsMinorVersion,
    ],
):
    __prompt_id__ = "used-by-ci-dont-delete-no-params"
    __prompt_major_version__ = "1"
    __execution_context_class__ = UsedByCiDontDeleteNoParamsExecutionContext
