############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from typing import Union  # noqa: F401

import pydantic  # noqa: F401

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer


class QuestionAnswererParams(FrozenModel):
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    model: str = pydantic.Field(..., alias="model")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")


class QuestionAnswererTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "content": "content",
        "documents": "documents",
        "idx": "idx",
        "question": "question",
    }

    def system(
        self,
    ) -> str:
        return self._render(
            "system",
        )

    def user(
        self,
        *,
        documents: str,
        question: str,
    ) -> str:
        return self._render(
            "user",
            documents=documents,
            question=question,
        )

    def user_doc(
        self,
        *,
        content: str,
        idx: str,
    ) -> str:
        return self._render(
            "user/doc",
            content=content,
            idx=idx,
        )


class QuestionAnswererExecutionContext(
    PromptExecutionContext[
        QuestionAnswererParams,
        QuestionAnswererTemplateRenderer,
    ],
):
    __params_class__ = QuestionAnswererParams
    __template_renderer_class__ = QuestionAnswererTemplateRenderer


class QuestionAnswererPromptManager(
    AutoblocksPromptManager[QuestionAnswererExecutionContext],
):
    __prompt_id__ = "question-answerer"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = QuestionAnswererExecutionContext


class TextSummarizationParams(FrozenModel):
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    model: str = pydantic.Field(..., alias="model")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")


class TextSummarizationTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "document": "document",
        "lang": "lang",
        "languageRequirement": "language_requirement",
        "tone": "tone",
        "toneRequirement": "tone_requirement",
    }

    def system(
        self,
        *,
        language_requirement: str,
        tone_requirement: str,
    ) -> str:
        return self._render(
            "system",
            language_requirement=language_requirement,
            tone_requirement=tone_requirement,
        )

    def user(
        self,
        *,
        document: str,
    ) -> str:
        return self._render(
            "user",
            document=document,
        )

    def util_language(
        self,
        *,
        lang: str,
    ) -> str:
        return self._render(
            "util/language",
            lang=lang,
        )

    def util_tone(
        self,
        *,
        tone: str,
    ) -> str:
        return self._render(
            "util/tone",
            tone=tone,
        )


class TextSummarizationExecutionContext(
    PromptExecutionContext[
        TextSummarizationParams,
        TextSummarizationTemplateRenderer,
    ],
):
    __params_class__ = TextSummarizationParams
    __template_renderer_class__ = TextSummarizationTemplateRenderer


class TextSummarizationPromptManager(
    AutoblocksPromptManager[TextSummarizationExecutionContext],
):
    __prompt_id__ = "text-summarization"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = TextSummarizationExecutionContext


class UsedByCiDontDeleteParams(FrozenModel):
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    model: str = pydantic.Field(..., alias="model")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")


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


class UsedByCiDontDeletePromptManager(
    AutoblocksPromptManager[UsedByCiDontDeleteExecutionContext],
):
    __prompt_id__ = "used-by-ci-dont-delete"
    __prompt_major_version__ = "2"
    __execution_context_class__ = UsedByCiDontDeleteExecutionContext


class UsedByCiDontDeleteNoParamsParams(FrozenModel):
    pass


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
        UsedByCiDontDeleteNoParamsParams,
        UsedByCiDontDeleteNoParamsTemplateRenderer,
    ],
):
    __params_class__ = UsedByCiDontDeleteNoParamsParams
    __template_renderer_class__ = UsedByCiDontDeleteNoParamsTemplateRenderer


class UsedByCiDontDeleteNoParamsPromptManager(
    AutoblocksPromptManager[UsedByCiDontDeleteNoParamsExecutionContext],
):
    __prompt_id__ = "used-by-ci-dont-delete-no-params"
    __prompt_major_version__ = "1"
    __execution_context_class__ = UsedByCiDontDeleteNoParamsExecutionContext
