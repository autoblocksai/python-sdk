import json
import os
from enum import Enum
from http import HTTPStatus
from unittest import mock

import pydantic
import pytest

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.error import IncompatiblePromptSnapshotError
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


class MyMinorVersion(Enum):
    v0 = "0"
    LATEST = "latest"


class MyPromptManager(
    AutoblocksPromptManager[
        MyExecutionContext,
        MyMinorVersion,
    ],
):
    __prompt_id__ = "my-prompt-id"
    __prompt_major_version__ = "1"
    __execution_context_class__ = MyExecutionContext


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_SNAPSHOTS": json.dumps({MyPromptManager.__prompt_id__: "mock-snapshot-id"}),
    },
)
def test_uses_prompt_snapshot(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/snapshots/mock-snapshot-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        json=dict(
            id="my-prompt-id",
            version="snapshot:mock-snapshot-id",
            templates=[
                dict(
                    id="my-template",
                    version="snapshot:mock-snapshot-id",
                    template="Hello, {{ name }}! The weather is {{ weather }} today!!!",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(MyMinorVersion.v0)
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_SNAPSHOTS": json.dumps({MyPromptManager.__prompt_id__: "mock-snapshot-id"}),
    },
)
def test_uses_prompt_snapshot_when_version_is_latest(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/snapshots/mock-snapshot-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        json=dict(
            id="my-prompt-id",
            version="snapshot:mock-snapshot-id",
            templates=[
                dict(
                    id="my-template",
                    version="snapshot:mock-snapshot-id",
                    template="Hello, {{ name }}! The weather is {{ weather }} today!!!",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(MyMinorVersion.LATEST)
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today!!!"

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_SNAPSHOTS": json.dumps({"some-other-prompt-id": "mock-snapshot-id"}),
    },
)
def test_uses_configured_version_if_snapshot_is_for_different_prompt(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            templates=[
                dict(
                    id="my-template",
                    version="1.0",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(MyMinorVersion.v0)
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_PROMPT_SNAPSHOTS": json.dumps({MyPromptManager.__prompt_id__: "mock-snapshot-id"}),
    },
)
def test_raises_if_prompt_is_incompatible(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/snapshots/mock-snapshot-id/validate",
        method="POST",
        match_headers={"Authorization": "Bearer mock-api-key"},
        match_content=make_expected_body(
            dict(
                majorVersion=1,
            ),
        ),
        # If the snapshot prompt ID matches the manager's prompt ID but the snapshot is
        # incompatible, the endpoint will return a 409.
        status_code=HTTPStatus.CONFLICT,
    )

    with pytest.raises(IncompatiblePromptSnapshotError) as exc:
        MyPromptManager(MyMinorVersion.v0)

    assert str(exc.value) == (
        "Can't override 'MyPromptManager' with prompt snapshot 'mock-snapshot-id' "
        "because it is not compatible with major version '1'."
    )

    assert len(httpx_mock.get_requests()) == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        # Note that AUTOBLOCKS_CLI_SERVER_ADDRESS is not set
        "AUTOBLOCKS_PROMPT_SNAPSHOTS": json.dumps({MyPromptManager.__prompt_id__: "mock-snapshot-id"}),
    },
)
def test_ignores_snapshot_id_if_not_in_test_run_context(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/my-prompt-id/major/1/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-prompt-id",
            version="1.0",
            templates=[
                dict(
                    id="my-template",
                    version="1.0",
                    template="Hello, {{ name }}! The weather is {{ weather }} today.",
                ),
            ],
        ),
    )

    mgr = MyPromptManager(MyMinorVersion.v0)
    with mgr.exec() as p:
        rendered = p.render.my_template(name="Nicole", weather="sunny")
        assert rendered == "Hello, Nicole! The weather is sunny today."

    assert len(httpx_mock.get_requests()) == 1
