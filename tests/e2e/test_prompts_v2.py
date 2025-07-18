import pytest

from tests.e2e.prompts_v2.apps import ci_app

pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api-v2.autoblocks.ai"])


def test_app_sdk_test_prompt_basic_v1():
    """Test the app_sdk_test.prompt_basic in major version 1."""
    mgr = ci_app.prompt_basic_prompt_manager(
        major_version="1",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"

        assert (
            ctx.render_template.template_a(  # type: ignore[union-attr]
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today."
        )

        track_info = ctx.track()

        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("1.")
        assert track_info["appId"] == "b5sz3k5d61w9f8325fhxuxkr"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1


def test_app_sdk_test_prompt_basic_v2():
    """Test the app_sdk_test.prompt_basic in major version 2."""
    mgr = ci_app.prompt_basic_prompt_manager(
        major_version="2",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"
        assert ctx.params.max_completion_tokens == 256  # type: ignore[union-attr]

        # Test template rendering
        assert (
            ctx.render_template.template_c(  # type: ignore[union-attr]
                first_name="Alice",
            )
            == "Hello, Alice!"
        )

        # Check tracking info
        track_info = ctx.track()
        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("2.")
        assert track_info["appId"] == "b5sz3k5d61w9f8325fhxuxkr"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1
