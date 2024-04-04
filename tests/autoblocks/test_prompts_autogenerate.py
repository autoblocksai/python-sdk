import os
from unittest import mock

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.autogenerate import infer_type
from autoblocks._impl.prompts.autogenerate import parse_template_params
from autoblocks._impl.prompts.autogenerate import to_snake_case
from autoblocks._impl.prompts.autogenerate import to_title_case
from autoblocks._impl.prompts.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.models import AutogeneratePromptConfig
from autoblocks._impl.prompts.models import AutogeneratePromptsConfig

# Show full diff in unittest
# import unittest
# unittest.util._MAX_LENGTH = 2000


def test_to_title_case():
    assert to_title_case("hello") == "Hello"
    assert to_title_case("helloWorld") == "HelloWorld"
    assert to_title_case("hello world") == "HelloWorld"
    assert to_title_case("Hello World") == "HelloWorld"
    assert to_title_case("hello_world") == "HelloWorld"
    assert to_title_case("hello-world") == "HelloWorld"
    assert to_title_case("hello/world") == "HelloWorld"
    assert to_title_case("hello123world") == "Hello123world"
    assert to_title_case("hello-123-world") == "Hello123World"
    assert to_title_case("hello-123") == "Hello123"
    assert to_title_case("123hello-world") == "HelloWorld"


def test_to_snake_case():
    assert to_snake_case("hello") == "hello"
    assert to_snake_case("helloWorld") == "hello_world"
    assert to_snake_case("hello world") == "hello_world"
    assert to_snake_case("hello    world") == "hello_world"
    assert to_snake_case("Hello World") == "hello_world"
    assert to_snake_case("hello_world") == "hello_world"
    assert to_snake_case("hello___world") == "hello_world"
    assert to_snake_case("hello-world") == "hello_world"
    assert to_snake_case("hello---world") == "hello_world"
    assert to_snake_case("hello/world") == "hello_world"
    assert to_snake_case("Hello/World") == "hello_world"
    assert to_snake_case("hello123world") == "hello123world"
    assert to_snake_case("hello-123-world") == "hello_123_world"
    assert to_snake_case("hello-123") == "hello_123"
    assert to_snake_case("123hello-world") == "hello_world"


def test_parse_template_params():
    assert parse_template_params("Hello") == []
    assert parse_template_params("Hello, {{ name }}!") == ["name"]
    assert parse_template_params("Hello, {{ name }}! My name is {{ name }}.") == ["name"]
    assert parse_template_params("{{ c }} {{ b }} {{a}}") == ["a", "b", "c"]
    assert parse_template_params("{{ param with spaces }}") == ["param with spaces"]


def test_infer_type():
    assert infer_type("") == "str"
    assert infer_type(0) == "Union[float, int]"
    assert infer_type(0.0) == "Union[float, int]"
    assert infer_type(True) == "bool"
    assert infer_type(False) == "bool"
    assert infer_type([""]) == "list[str]"
    assert infer_type([]) is None
    assert infer_type({}) is None
    assert infer_type(None) is None


MOCK_PROMPTS_API_RESPONSE = [
    {
        "id": "prompt-a",
        "params": {
            "params": {
                "frequencyPenalty": 0,
                "maxTokens": 256,
                "model": "gpt-4",
                "presencePenalty": 0.3,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 1,
            },
            "version": "1.0",
        },
        "templates": [
            {
                "id": "template-a",
                "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                "version": "1.0",
            },
            {
                "id": "template-b",
                "template": "Hello, {{ name-1 }}! My name is {{ name-2 }}.",
                "version": "1.0",
            },
        ],
        "version": "1.0",
    },
    {
        "id": "prompt-b",
        "templates": [
            {
                "id": "template-a",
                "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                "version": "1.0",
            },
            {
                "id": "template-b",
                "template": "Hello, {{ name1 }}! My name is {{ name2 }}.",
                "version": "1.0",
            },
            {
                "id": "template-c",
                "template": "I am template c and I have no params",
                "version": "1.0",
            },
        ],
        "version": "2.0",
    },
    {
        "id": "prompt-b",
        "params": {
            "params": {
                "frequencyPenalty": 0,
                "maxTokens": 256,
                "model": "gpt-4",
                "presencePenalty": -0.3,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 1,
            },
            "version": "1.1",
        },
        "templates": [
            {
                "id": "template-a",
                "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                "version": "1.0",
            },
            {
                "id": "template-b",
                "template": "Hello, {{ name1 }}! My name is {{ name2 }}.",
                "version": "1.0",
            },
        ],
        "version": "1.1",
    },
    {
        "id": "prompt-b",
        "params": {
            "params": {
                "frequencyPenalty": 0,
                "maxTokens": 256,
                "model": "gpt-4",
                "presencePenalty": 0.3,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 1,
            },
            "version": "1.0",
        },
        "templates": [
            {
                "id": "template-a",
                "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                "version": "1.0",
            },
            {
                "id": "template-b",
                "template": "Hello, {{ name1 }}! My name is {{ name2 }}.",
                "version": "1.0",
            },
        ],
        "version": "1.0",
    },
]

PROMPT_C_UNDEPLOYED_RESPONSE = {
    "id": "prompt-c",
    "params": {
        "params": {
            "frequencyPenalty": 0,
            "maxTokens": 256,
            "model": "gpt-4",
            "presencePenalty": 0.3,
            "stopSequences": [],
            "temperature": 0.7,
            "topP": 1,
        },
        "version": "1.0",
    },
    "templates": [
        {
            "id": "template",
            "template": "Hello !!!",
            "version": "1.0",
        },
    ],
    "version": "undeployed",
}


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_write(httpx_mock):
    config = AutogeneratePromptsConfig(
        outfile="test.py",
        prompts=[
            AutogeneratePromptConfig(
                id="prompt-a",
                major_versions=["1"],
            ),
            AutogeneratePromptConfig(
                id="prompt-b",
                # Test that it works with numbers
                major_versions=[1, 2],  # type: ignore
            ),
            AutogeneratePromptConfig(
                id="prompt-c",
                major_versions=["dangerously-use-undeployed"],
            ),
        ],
    )

    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts",
        method="GET",
        status_code=200,
        json=MOCK_PROMPTS_API_RESPONSE,
        match_headers={"Authorization": "Bearer mock-api-key"},
    )
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-a/major/undeployed/minor/undeployed",
        method="GET",
        status_code=404,
        match_headers={"Authorization": "Bearer mock-api-key"},
    )
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-b/major/undeployed/minor/undeployed",
        method="GET",
        status_code=404,
        match_headers={"Authorization": "Bearer mock-api-key"},
    )
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-c/major/undeployed/minor/undeployed",
        method="GET",
        status_code=200,
        json=PROMPT_C_UNDEPLOYED_RESPONSE,
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    m = mock.mock_open()

    with mock.patch("autoblocks._impl.prompts.autogenerate.open", m):
        write_generated_code_for_config(config)

    expected = """############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from enum import Enum
from typing import Union  # noqa: F401

import pydantic

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer


class PromptAParams(FrozenModel):
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    model: str = pydantic.Field(..., alias="model")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")


class PromptATemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "name-1": "name_1",
        "name-2": "name_2",
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
        name_1: str,
        name_2: str,
    ) -> str:
        return self._render(
            "template-b",
            name_1=name_1,
            name_2=name_2,
        )


class PromptAExecutionContext(
    PromptExecutionContext[
        PromptAParams,
        PromptATemplateRenderer,
    ],
):
    __params_class__ = PromptAParams
    __template_renderer_class__ = PromptATemplateRenderer


class PromptAMinorVersion(Enum):
    v0 = "0"
    LATEST = "latest"


class PromptAPromptManager(
    AutoblocksPromptManager[
        PromptAExecutionContext,
        PromptAMinorVersion,
    ],
):
    __prompt_id__ = "prompt-a"
    __prompt_major_version__ = "1"
    __execution_context_class__ = PromptAExecutionContext


class PromptB1Params(FrozenModel):
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    model: str = pydantic.Field(..., alias="model")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")


class PromptB1TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "name1": "name1",
        "name2": "name2",
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
        name1: str,
        name2: str,
    ) -> str:
        return self._render(
            "template-b",
            name1=name1,
            name2=name2,
        )


class PromptB1ExecutionContext(
    PromptExecutionContext[
        PromptB1Params,
        PromptB1TemplateRenderer,
    ],
):
    __params_class__ = PromptB1Params
    __template_renderer_class__ = PromptB1TemplateRenderer


class PromptB1MinorVersion(Enum):
    v0 = "0"
    v1 = "1"
    LATEST = "latest"


class PromptB1PromptManager(
    AutoblocksPromptManager[
        PromptB1ExecutionContext,
        PromptB1MinorVersion,
    ],
):
    __prompt_id__ = "prompt-b"
    __prompt_major_version__ = "1"
    __execution_context_class__ = PromptB1ExecutionContext


class PromptB2Params(FrozenModel):
    pass


class PromptB2TemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "name1": "name1",
        "name2": "name2",
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
        name1: str,
        name2: str,
    ) -> str:
        return self._render(
            "template-b",
            name1=name1,
            name2=name2,
        )

    def template_c(
        self,
    ) -> str:
        return self._render(
            "template-c",
        )


class PromptB2ExecutionContext(
    PromptExecutionContext[
        PromptB2Params,
        PromptB2TemplateRenderer,
    ],
):
    __params_class__ = PromptB2Params
    __template_renderer_class__ = PromptB2TemplateRenderer


class PromptB2MinorVersion(Enum):
    v0 = "0"
    LATEST = "latest"


class PromptB2PromptManager(
    AutoblocksPromptManager[
        PromptB2ExecutionContext,
        PromptB2MinorVersion,
    ],
):
    __prompt_id__ = "prompt-b"
    __prompt_major_version__ = "2"
    __execution_context_class__ = PromptB2ExecutionContext


class PromptCUndeployedParams(FrozenModel):
    frequency_penalty: Union[float, int] = pydantic.Field(..., alias="frequencyPenalty")
    max_tokens: Union[float, int] = pydantic.Field(..., alias="maxTokens")
    model: str = pydantic.Field(..., alias="model")
    presence_penalty: Union[float, int] = pydantic.Field(..., alias="presencePenalty")
    temperature: Union[float, int] = pydantic.Field(..., alias="temperature")
    top_p: Union[float, int] = pydantic.Field(..., alias="topP")


class PromptCUndeployedTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {}

    def template(
        self,
    ) -> str:
        return self._render(
            "template",
        )


class PromptCUndeployedExecutionContext(
    PromptExecutionContext[
        PromptCUndeployedParams,
        PromptCUndeployedTemplateRenderer,
    ],
):
    __params_class__ = PromptCUndeployedParams
    __template_renderer_class__ = PromptCUndeployedTemplateRenderer


class PromptCUndeployedMinorVersion(Enum):
    DANGEROUSLY_USE_UNDEPLOYED = "undeployed"


class PromptCUndeployedPromptManager(
    AutoblocksPromptManager[
        PromptCUndeployedExecutionContext,
        PromptCUndeployedMinorVersion,
    ],
):
    __prompt_id__ = "prompt-c"
    __prompt_major_version__ = "undeployed"
    __execution_context_class__ = PromptCUndeployedExecutionContext
"""

    m.assert_called_once_with("test.py", "w")
    m().write.assert_called_once()
    write_called_with = m().write.call_args[0][0]
    assert write_called_with == expected
