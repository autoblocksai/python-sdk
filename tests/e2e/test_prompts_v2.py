import pytest

from autoblocks._impl.tracer import AutoblocksTracer
from tests.e2e.autoblocks_prompts import app_sdk_test
from tests.e2e.autoblocks_prompts import sdk_test_app_v3

pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["dev-api.autoblocks.ai"])

tracer = AutoblocksTracer()


def test_app_sdk_test_prompt_basic_v1():
    """Test the app_sdk_test.prompt_basic in major version 1."""
    mgr = app_sdk_test.prompt_basic_prompt_manager(
        major_version="1",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.max_tokens == 256
        assert ctx.params.model == "gpt-4o"
        assert ctx.params.temperature == 0.7
        assert ctx.params.top_p == 1
        assert ctx.params.frequency_penalty == 0
        assert ctx.params.presence_penalty == 0
        assert ctx.params.stop_sequences == []

        assert (
            ctx.render_template.template_a(
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today."
        )

        assert (
            ctx.render_template.template_b(
                name="Alice",
            )
            == "Hello, {{ optional? }}! My name is Alice."
        )

        track_info = ctx.track()

        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("1.")
        assert track_info["appId"] == "jqg74mpzzovssq38j055yien"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 2


def test_app_sdk_test_prompt_basic_v2():
    """Test the app_sdk_test.prompt_basic in major version 2."""
    mgr = app_sdk_test.prompt_basic_prompt_manager(
        major_version="2",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"
        assert ctx.params.top_k == 0
        assert ctx.params.seed == 4096

        # Test template rendering
        assert (
            ctx.render_template.template_c(
                first_name="Alice",
            )
            == "Hello, Alice!"
        )

        # Check tracking info
        track_info = ctx.track()
        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("2.")
        assert track_info["appId"] == "jqg74mpzzovssq38j055yien"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1


def test_sdk_test_app_v3_prompt_basic():
    """Test the sdk_test_app_v3.prompt_basic."""
    mgr = sdk_test_app_v3.prompt_basic_prompt_manager(
        minor_version="0",
    )

    with mgr.exec() as ctx:

        track_info = ctx.track()
        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("1.")
        assert track_info["appId"] == "n8qq0j4izc3t7p00gcx8apcg"


def test_sdk_test_app_v3_undeployed_prompt():
    """Test an undeployed prompt from sdk_test_app_v3."""
    mgr = sdk_test_app_v3.do_not_deploy_prompt_manager(
        minor_version="latest",
    )

    with mgr.exec() as ctx:

        track_info = ctx.track()
        print(track_info)
        assert track_info["id"] == "do-not-deploy"
        assert track_info["version"] == "revision:bgp4ilyn5xx8dmndw1yi95pw"
        assert track_info["appId"] == "n8qq0j4izc3t7p00gcx8apcg"
