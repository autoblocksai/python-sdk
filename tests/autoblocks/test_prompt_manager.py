import json
import os
from http import HTTPStatus
from unittest import mock

import pydantic
import pytest

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.error import IncompatiblePromptRevisionError
from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.renderer import TemplateRenderer
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import make_expected_body


class MyClassParams(pydantic.BaseModel):
    pass


class MyTemplateRenderer(TemplateRenderer):
    __name_mapper__ = {
        "name": "name",
        "weather": "weather",
    }

    def my_template(
        self,
        *,
        name: str,
        weather: str,
    ) -> str:
        return self._render(
            "my-template",
            name=name,
            weather=weather,
        )


class MyExecutionContext(
    PromptExecutionContext[
        MyClassParams,
        MyTemplateRenderer,
    ],
):
    __params_class__ = MyClassParams
    __template_renderer_class__ = MyTemplateRenderer


class MyPromptManager(
    AutoblocksPromptManager[MyExecutionContext],
):
    __prompt_id__ = "my-prompt-id"
    __prompt_major_version__ = "1"
    __execution_context_class__ = MyExecutionContext


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_REVISIONS": json.dumps({MyPromptManager.__prompt_id__: "mock-revision-id"}),
    },
)
def test_uses_prompt_revision(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/revisions/mock-revision-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        json=dict(
            id="my-prompt-id",
            version="revision:mock-revision-id",
            revisionId="mock-revision-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today!!!",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_REVISIONS": json.dumps({MyPromptManager.__prompt_id__: "mock-revision-id"}),
    },
)
def test_uses_prompt_revision_when_version_is_latest(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/revisions/mock-revision-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        json=dict(
            id="my-prompt-id",
            version="revision:mock-revision-id",
            revisionId="mock-revision-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today!!!",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(minor_version="latest")
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_REVISIONS": json.dumps({"some-other-prompt-id": "mock-revision-id"}),
    },
)
def test_uses_configured_version_if_revision_is_for_different_prompt(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            revisionId="mock-revision-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_REVISIONS": json.dumps({MyPromptManager.__prompt_id__: "mock-revision-id"}),
    },
)
def test_raises_if_prompt_is_incompatible(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/revisions/mock-revision-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        # If the revision's prompt ID matches the manager's prompt ID but the revision is
        # incompatible, the endpoint will return a 409.
        status_code=HTTPStatus.CONFLICT,
    )

    with pytest.raises(IncompatiblePromptRevisionError) as exc:
        MyPromptManager(minor_version="0")

    assert str(exc.value) == (
        "Can't override prompt 'MyPromptManager' with revision 'mock-revision-id' "
        "because it is not compatible with major version '1'."
    )

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        # Note that AUTOBLOCKS_CLI_SERVER_ADDRESS is not set
        "AUTOBLOCKS_PROMPT_REVISIONS": json.dumps({MyPromptManager.__prompt_id__: "mock-revision-id"}),
    },
)
def test_ignores_revision_id_if_not_in_test_run_context(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            revisionId="mock-revision-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1
