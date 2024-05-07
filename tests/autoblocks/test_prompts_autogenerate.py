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
                    "template": "Hello, {{ name-1 }}! My name is {{ name-2 }}.",
                },
            ],
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
                },
            },
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
            ],
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
