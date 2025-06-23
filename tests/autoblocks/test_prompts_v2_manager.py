import json
import os
from http import HTTPStatus
from typing import Any
from unittest import mock

import pytest

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.prompts.error import IncompatiblePromptRevisionError
from autoblocks.prompts.v2.context import PromptExecutionContext
from autoblocks.prompts.v2.manager import AutoblocksPromptManager
from autoblocks.prompts.v2.models import FrozenModel
from autoblocks.prompts.v2.renderer import TemplateRenderer
from autoblocks.prompts.v2.renderer import ToolRenderer
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import make_expected_body


class MyV2Params(FrozenModel):
    pass


class MyV2TemplateRenderer(TemplateRenderer):
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


class MyV2ToolRenderer(ToolRenderer):
    __name_mapper__ = {
        "description": "description",
    }

    def my_tool(
        self,
        *,
        description: str,
    ) -> dict[str, Any]:
        return self._render(
            "my-tool",
            description=description,
        )


class MyV2ExecutionContext(
    PromptExecutionContext[MyV2Params, MyV2TemplateRenderer, MyV2ToolRenderer],
):
    __params_class__ = MyV2Params
    __template_renderer_class__ = MyV2TemplateRenderer
    __tool_renderer_class__ = MyV2ToolRenderer


class MyV2PromptManager(
    AutoblocksPromptManager[MyV2ExecutionContext],
):
    __app_id__ = "test-app-id"
    __prompt_id__ = "my-prompt-id"
    __prompt_major_version__ = "1"
    __execution_context_class__ = MyV2ExecutionContext


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_OVERRIDES": json.dumps({"promptRevisions": {MyV2PromptManager.__prompt_id__: "mock-revision-id"}}),
    },
)
def test_uses_prompt_revision(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/revisions/mock-revision-id/validate",
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
            params=dict(params={}),
            tools=[dict(name="my-tool", description="{{ description }}")],
            toolsParams=[dict(name="my-tool", params=["description"])],
        ),
    )

    mgr = MyV2PromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render_template.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"
        # Test that the override prompt data is being used
        assert p.track()["revisionId"] == "mock-revision-id"
        assert p.track()["version"] == "revision:mock-revision-id"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_OVERRIDES": json.dumps({"promptRevisions": {MyV2PromptManager.__prompt_id__: "mock-revision-id"}}),
    },
)
def test_uses_prompt_revision_when_version_is_latest(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/revisions/mock-revision-id/validate",
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
            params=dict(params={}),
            tools=[dict(name="my-tool", description="{{ description }}")],
            toolsParams=[dict(name="my-tool", params=["description"])],
        ),
    )

    mgr = MyV2PromptManager(minor_version="latest")
    with mgr.exec() as p:
        rendered = p.render_template.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_OVERRIDES": json.dumps({"promptRevisions": {"some-other-prompt-id": "mock-revision-id"}}),
    },
)
def test_uses_configured_version_if_revision_is_for_different_prompt(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            revisionId="mock-revision-id",
            appId="test-app-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyV2PromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render_template.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_OVERRIDES": json.dumps({"promptRevisions": {MyV2PromptManager.__prompt_id__: "mock-revision-id"}}),
    },
)
def test_raises_if_prompt_is_incompatible(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/revisions/mock-revision-id/validate",
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
        MyV2PromptManager(minor_version="0")

    assert str(exc.value) == (
        "Can't override prompt 'MyV2PromptManager' with revision 'mock-revision-id' "
        "because it is not compatible with major version '1'."
    )

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        # Note that AUTOBLOCKS_CLI_SERVER_ADDRESS is not set
        "AUTOBLOCKS_OVERRIDES": json.dumps({"promptRevisions": {MyV2PromptManager.__prompt_id__: "mock-revision-id"}}),
    },
)
def test_ignores_revision_id_if_not_in_test_run_context(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            revisionId="mock-revision-id",
            appId="test-app-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyV2PromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render_template.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_OVERRIDES_PROMPT_REVISIONS": json.dumps({MyV2PromptManager.__prompt_id__: "legacy-revision-id"}),
    },
)
def test_falls_back_to_legacy_format(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/test-app-id/prompts/my-prompt-id/revisions/legacy-revision-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        json=dict(
            id="my-prompt-id",
            version="revision:legacy-revision-id",
            revisionId="legacy-revision-id",
            templates=[
                dict(
                    id="my-template",
                    template="Hello, {{ name }}! Legacy format works!",
                ),
            ],
        ),
    )

    mgr = MyV2PromptManager(minor_version="0")
    with mgr.exec() as p:
        rendered = p.render_template.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! Legacy format works!"

    assert len(httpx_mock.get_requests()) == 1
