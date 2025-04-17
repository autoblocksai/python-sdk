import pytest

from tests.e2e.autoblocks_prompts import app_sdk_test
from tests.e2e.autoblocks_prompts import sdk_test_app_v3

pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api-v2.autoblocks.ai"])


@pytest.mark.skip
def test_app_sdk_test_prompt_basic_v1():
    """Test the app_sdk_test.prompt_basic in major version 1."""
    mgr = app_sdk_test.prompt_basic_prompt_manager(
        major_version="1",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"

        assert (
            ctx.render_template.template_a(
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today."
        )

        track_info = ctx.track()

        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("1.")
        assert track_info["appId"] == "uu95770k1muazxpbi4gazisr"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1


@pytest.mark.skip
def test_app_sdk_test_prompt_basic_v2():
    """Test the app_sdk_test.prompt_basic in major version 2."""
    mgr = app_sdk_test.prompt_basic_prompt_manager(
        major_version="2",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"
        assert ctx.params.max_tokens == 256

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
        assert track_info["appId"] == "uu95770k1muazxpbi4gazisr"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1


@pytest.mark.skip
def test_sdk_test_app_v3_undeployed_prompt():
    """Test an undeployed prompt from sdk_test_app_v3."""
    mgr = sdk_test_app_v3.prompt_basic_prompt_manager(
        minor_version="latest",
    )

    with mgr.exec() as ctx:
        track_info = ctx.track()

        assert track_info["id"] == "prompt-basic"
        assert track_info["version"] == "revision:jf6a0401grzkg2nfn20gx4ox"
        assert track_info["appId"] == "b108cei22gakuuujcbtnrt2a"
