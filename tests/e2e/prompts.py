############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from typing import Any  # noqa: F401
from typing import Dict  # noqa: F401
from typing import Union  # noqa: F401

import pydantic  # noqa: F401

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer
from autoblocks.prompts.renderer import ToolRenderer


class QuestionAnswererParams(FrozenModel):
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    max_completion_tokens: Union[float, int] = pydantic.Field(..., alias="maxCompletionTokens")
    model: str = pydantic.Field(..., alias="model")


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


class QuestionAnswererToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class QuestionAnswererExecutionContext(
    PromptExecutionContext[
        QuestionAnswererParams,
        QuestionAnswererTemplateRenderer,
        QuestionAnswererToolRenderer,
    ],
):
    __params_class__ = QuestionAnswererParams
    __template_renderer_class__ = QuestionAnswererTemplateRenderer
    __tool_renderer_class__ = QuestionAnswererToolRenderer


class QuestionAnswererPromptManager(
    AutoblocksPromptManager[QuestionAnswererExecutionContext],
):
    __prompt_id__ = "question-answerer"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = QuestionAnswererExecutionContext


class TextSummarizationParams(FrozenModel):
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    max_completion_tokens: Union[float, int] = pydantic.Field(..., alias="maxCompletionTokens")
    model: str = pydantic.Field(..., alias="model")


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


class TextSummarizationToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class TextSummarizationExecutionContext(
    PromptExecutionContext[
        TextSummarizationParams,
        TextSummarizationTemplateRenderer,
        TextSummarizationToolRenderer,
    ],
):
    __params_class__ = TextSummarizationParams
    __template_renderer_class__ = TextSummarizationTemplateRenderer
    __tool_renderer_class__ = TextSummarizationToolRenderer


class TextSummarizationPromptManager(
    AutoblocksPromptManager[TextSummarizationExecutionContext],
):
    __prompt_id__ = "text-summarization"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = TextSummarizationExecutionContext


class UsedByCiDontDeleteParams(FrozenModel):
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    max_completion_tokens: Union[float, int] = pydantic.Field(..., alias="maxCompletionTokens")
    seed: Union[float, int] = pydantic.Field(..., alias="seed")
    model: str = pydantic.Field(..., alias="model")
    response_format: Dict[str, Any] = pydantic.Field(..., alias="responseFormat")


class UsedByCiDontDeleteTemplateRenderer(TemplateRenderer):
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

    def template_c(
        self,
    ) -> str:
        return self._render(
            "template-c",
        )


class UsedByCiDontDeleteToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class UsedByCiDontDeleteExecutionContext(
    PromptExecutionContext[
        UsedByCiDontDeleteParams,
        UsedByCiDontDeleteTemplateRenderer,
        UsedByCiDontDeleteToolRenderer,
    ],
):
    __params_class__ = UsedByCiDontDeleteParams
    __template_renderer_class__ = UsedByCiDontDeleteTemplateRenderer
    __tool_renderer_class__ = UsedByCiDontDeleteToolRenderer


class UsedByCiDontDeletePromptManager(
    AutoblocksPromptManager[UsedByCiDontDeleteExecutionContext],
):
    __prompt_id__ = "used-by-ci-dont-delete"
    __prompt_major_version__ = "6"
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


class UsedByCiDontDeleteNoParamsToolRenderer(ToolRenderer):
    __name_mapper__ = {}


class UsedByCiDontDeleteNoParamsExecutionContext(
    PromptExecutionContext[
        UsedByCiDontDeleteNoParamsParams,
        UsedByCiDontDeleteNoParamsTemplateRenderer,
        UsedByCiDontDeleteNoParamsToolRenderer,
    ],
):
    __params_class__ = UsedByCiDontDeleteNoParamsParams
    __template_renderer_class__ = UsedByCiDontDeleteNoParamsTemplateRenderer
    __tool_renderer_class__ = UsedByCiDontDeleteNoParamsToolRenderer


class UsedByCiDontDeleteNoParamsPromptManager(
    AutoblocksPromptManager[UsedByCiDontDeleteNoParamsExecutionContext],
):
    __prompt_id__ = "used-by-ci-dont-delete-no-params"
    __prompt_major_version__ = "1"
    __execution_context_class__ = UsedByCiDontDeleteNoParamsExecutionContext


class UsedByCiDontDeleteWithToolsParams(FrozenModel):
    pass


class UsedByCiDontDeleteWithToolsTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def system(
        self,
    ) -> str:
        return self._render(
            "system",
        )


class UsedByCiDontDeleteWithToolsToolRenderer(ToolRenderer):
    __name_mapper__ = {
        "description": "description",
    }

    def my_tool(
        self,
        *,
        description: str,
    ) -> Dict[str, Any]:
        return self._render(
            "MyTool",
            description=description,
        )


class UsedByCiDontDeleteWithToolsExecutionContext(
    PromptExecutionContext[
        UsedByCiDontDeleteWithToolsParams,
        UsedByCiDontDeleteWithToolsTemplateRenderer,
        UsedByCiDontDeleteWithToolsToolRenderer,
    ],
):
    __params_class__ = UsedByCiDontDeleteWithToolsParams
    __template_renderer_class__ = UsedByCiDontDeleteWithToolsTemplateRenderer
    __tool_renderer_class__ = UsedByCiDontDeleteWithToolsToolRenderer


class UsedByCiDontDeleteWithToolsPromptManager(
    AutoblocksPromptManager[UsedByCiDontDeleteWithToolsExecutionContext],
):
    __prompt_id__ = "used-by-ci-dont-delete-with-tools"
    __prompt_major_version__ = "1"
    __execution_context_class__ = UsedByCiDontDeleteWithToolsExecutionContext
