import os
from unittest import mock

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.autogenerate import infer_type
from autoblocks._impl.prompts.autogenerate import to_snake_case
from autoblocks._impl.prompts.autogenerate import to_title_case
from autoblocks._impl.prompts.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.models import AutogeneratePromptConfig
from autoblocks._impl.prompts.models import AutogeneratePromptsConfig
from autoblocks._impl.prompts.placeholders import TemplatePlaceholder
from autoblocks._impl.prompts.placeholders import parse_placeholders_from_template

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


def test_parse_placeholders_from_template():
    assert parse_placeholders_from_template("Hello") == []
    assert parse_placeholders_from_template("Hello, {{ name }}!") == [
        TemplatePlaceholder(
            is_escaped=False,
            name="name",
        ),
    ]
    assert parse_placeholders_from_template("Hello, {{ name }}! My name is {{ name }}.") == [
        TemplatePlaceholder(
            is_escaped=False,
            name="name",
        ),
    ]
    assert parse_placeholders_from_template("{{ c }} {{ b }} {{a}}") == [
        TemplatePlaceholder(
            is_escaped=False,
            name="a",
        ),
        TemplatePlaceholder(
            is_escaped=False,
            name="b",
        ),
        TemplatePlaceholder(
            is_escaped=False,
            name="c",
        ),
    ]
    assert parse_placeholders_from_template("{{ param with spaces }} {{ param-with-hyphens }}") == [
        TemplatePlaceholder(
            is_escaped=False,
            name="param-with-hyphens",
        ),
    ]
    assert parse_placeholders_from_template("I am \\{{ escaped }} and I am {{ not }} escaped") == [
        TemplatePlaceholder(
            is_escaped=True,
            name="escaped",
        ),
        TemplatePlaceholder(
            is_escaped=False,
            name="not",
        ),
    ]
    assert parse_placeholders_from_template("\\{{ escaped }} \\{{ escaped }} {{ escaped }}") == [
        TemplatePlaceholder(
            is_escaped=False,
            name="escaped",
        ),
        TemplatePlaceholder(
            is_escaped=True,
            name="escaped",
        ),
    ]
    assert (
        parse_placeholders_from_template(
            """Please respond in the format:

{{
  "x": {{
    "y": 1
  }}
}}

Thanks!
"""
        )
        == []
    )


def test_infer_type():
    assert infer_type("") == "str"
    assert infer_type(0) == "Union[float, int]"
    assert infer_type(0.0) == "Union[float, int]"
    assert infer_type(True) == "bool"
    assert infer_type(False) == "bool"
    assert infer_type([""]) == "list[str]"
    assert infer_type([]) is None
    assert infer_type({}) == "Dict[str, Any]"
    assert infer_type({"a": 1}) == "Dict[str, Any]"
    assert infer_type(None) is None


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_write(httpx_mock, snapshot):
    config = AutogeneratePromptsConfig(
        outfile="test.py",
        prompts=[
            AutogeneratePromptConfig(
                id="prompt-a",
                major_version="1",
            ),
            AutogeneratePromptConfig(
                id="prompt-b",
                # Test that it works with numbers
                major_version=1,  # type: ignore
            ),
            AutogeneratePromptConfig(
                id="prompt-c",
                dangerously_use_undeployed_revision="latest",
            ),
            AutogeneratePromptConfig(
                id="prompt-d",
                dangerously_use_undeployed_revision="mock-specific-revision-id",
            ),
        ],
    )

    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-a/major/1/minor/latest",
        method="GET",
        status_code=200,
        json={
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
                    "seed": 4096,
                    "responseFormat": {"type": "json_object"},
                },
                "version": "1.0",
            },
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
                {
                    "id": "template-b",
                    "template": "Hello, {{ name-1 }}! My name is {{ name-2 }}. "
                    "Escaped \{{escaped}} placeholders should be ignored.",
                },
            ],
            "toolsParams": [],
            "version": "1.0",
            "revisionId": "mock-revision-id",
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-b/major/1/minor/latest",
        method="GET",
        status_code=200,
        json={
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
                    "seed": 4096,
                    "responseFormat": {"type": "json_object"},
                },
            },
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
            ],
            "toolsParams": [{"name": "tool-b", "params": ["description"]}],
            "version": "3.1",
            "revisionId": "mock-revision-id",
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-c/major/undeployed/minor/latest",
        method="GET",
        status_code=200,
        json={
            "id": "prompt-c",
            "params": None,
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
            ],
            "toolsParams": [],
            "version": "revision:mock-revision-id",
            "revisionId": "mock-revision-id",
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-d/major/undeployed/minor/mock-specific-revision-id",
        method="GET",
        status_code=200,
        json={
            "id": "prompt-c",
            "params": None,
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
            ],
            "toolsParams": [],
            "version": "revision:mock-specific-revision-id",
            "revisionId": "mock-specific-revision-id",
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    m = mock.mock_open()

    with mock.patch("autoblocks._impl.prompts.autogenerate.open", m):
        write_generated_code_for_config(config)

    m.assert_called_once_with("test.py", "w")
    m().write.assert_called_once()
    write_called_with = m().write.call_args[0][0]
    assert write_called_with == snapshot
