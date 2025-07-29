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
        major_version="4",
        minor_version="0",
    )

    with mgr.exec() as ctx:
        # Assert parameters
        assert ctx.params.model == "gpt-4o"
        assert ctx.params.max_completion_tokens == 256  # type: ignore[union-attr]

        # Test template rendering
        assert (
            ctx.render_template.template_c(  # type: ignore[union-attr,call-arg]
                first_name="Alice",
            )
            == "Hello, Alice!"
        )

        # Check tracking info
        track_info = ctx.track()
        assert track_info["id"] == "prompt-basic"
        assert track_info["version"].startswith("4.")
        assert track_info["appId"] == "b5sz3k5d61w9f8325fhxuxkr"
        assert "templates" in track_info
        assert len(track_info["templates"]) == 1


# Note: E2E tests for revision overrides would require real revision IDs
# and would be better suited for integration tests with actual API endpoints
def test_prompt_revision_override_structure():
    """Test that V2 prompts have the same structure as V1 for revision overrides."""
    # This test verifies that the manager has the necessary attributes for overrides
    mgr = ci_app.prompt_basic_prompt_manager(
        major_version="4",
        minor_version="0",
    )

    # Verify the manager has the required attributes for revision overrides
    assert hasattr(mgr, "_prompt_revision_override")
    assert hasattr(mgr, "__prompt_id__")
    assert hasattr(mgr, "__app_id__")
    assert mgr.__prompt_id__ == "prompt-basic"
    assert mgr.__app_id__ == "b5sz3k5d61w9f8325fhxuxkr"
