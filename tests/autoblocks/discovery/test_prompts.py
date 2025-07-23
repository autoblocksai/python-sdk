from unittest.mock import MagicMock
from unittest.mock import patch

from autoblocks._impl.prompts.v2.discovery.models import PromptData
from autoblocks._impl.prompts.v2.discovery.prompts import generate_params_class_code
from autoblocks._impl.prompts.v2.discovery.prompts import generate_prompt_implementations
from autoblocks._impl.prompts.v2.discovery.prompts import generate_version_implementations

try:
    from pydantic import AliasChoices
except ImportError:  # pragma: no cover - older pydantic
    AliasChoices = None  # type: ignore


class TestPrompts:
    def test_generate_params_class_code_empty(self):
        # Test params class generation with empty params
        title_case_id = "TestPrompt"
        version = "1"
        params: dict[str, object] = {}

        result = generate_params_class_code(title_case_id, version, params)

        # Check class definition and empty body
        assert "class _TestPromptV1Params(FrozenModel):" in result
        assert "    pass" in result

    def test_generate_params_class_code(self):
        # Test params class generation with typical params
        title_case_id = "TestPrompt"
        version = "1"
        params = {
            "temperature": 0.7,
            "maxCompletionTokens": 100,
            "model": "gpt-4",
            "isEnabled": True,
        }

        result = generate_params_class_code(title_case_id, version, params)

        # Check class definition and parameters
        assert "class _TestPromptV1Params(FrozenModel):" in result
        assert 'temperature: Union[float, int] = pydantic.Field(..., alias="temperature")' in result
        assert (
            "max_completion_tokens: Union[float, int] = pydantic.Field(..., "
            'alias="maxCompletionTokens", validation_alias=(AliasChoices("maxCompletionTokens", "maxTokens") if '
            'AliasChoices else "maxCompletionTokens"))' in result
        )
        assert '    model: str = pydantic.Field(..., alias="model")' in result
        assert '    is_enabled: bool = pydantic.Field(..., alias="isEnabled")' in result

    def test_generate_params_class_code_nested(self):
        # Test params class generation with nested params structure
        title_case_id = "TestPrompt"
        version = "1"
        params = {
            "params": {
                "temperature": 0.7,
                "maxCompletionTokens": 100,
            }
        }

        result = generate_params_class_code(title_case_id, version, params)

        # Check class definition and extracted parameters
        assert "class _TestPromptV1Params(FrozenModel):" in result
        assert 'temperature: Union[float, int] = pydantic.Field(..., alias="temperature")' in result
        assert (
            "max_completion_tokens: Union[float, int] = pydantic.Field(..., "
            'alias="maxCompletionTokens", validation_alias=(AliasChoices("maxCompletionTokens", "maxTokens") if '
            'AliasChoices else "maxCompletionTokens"))' in result
        )

    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_params_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_template_renderer_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_tool_renderer_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_execution_context_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_manager_class_code")
    def test_generate_version_implementations(self, mock_manager, mock_context, mock_tool, mock_template, mock_params):
        # Setup mocks
        mock_params.return_value = "params_class_code"
        mock_template.return_value = "template_renderer_code"
        mock_tool.return_value = "tool_renderer_code"
        mock_context.return_value = "execution_context_code"
        mock_manager.return_value = "manager_class_code"

        # Test version implementations generation
        title_case_id = "TestPrompt"
        version = "1"
        prompt_id = "test-prompt"
        app_id = "test-app"
        params = {"temperature": 0.7}
        templates = [{"id": "template1", "template": "Hello {{name}}"}]
        tools = [{"name": "tool1", "params": ["param1"]}]

        result = generate_version_implementations(title_case_id, version, prompt_id, app_id, params, templates, tools)

        # Check that mocks were called with correct parameters
        mock_params.assert_called_once_with(title_case_id, version, params)
        mock_template.assert_called_once_with(title_case_id, version, templates)
        mock_tool.assert_called_once_with(title_case_id, version, tools)
        mock_context.assert_called_once_with(title_case_id, version)
        mock_manager.assert_called_once_with(title_case_id, version, prompt_id, app_id)

        # Check the result contains all implementations
        assert len(result) == 5
        assert "params_class_code" in result
        assert "template_renderer_code" in result
        assert "tool_renderer_code" in result
        assert "execution_context_code" in result
        assert "manager_class_code" in result

    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_version_implementations")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_factory_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_manager_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.get_prompt_data")
    def test_generate_prompt_implementations_deployed(self, mock_get_data, mock_manager, mock_factory, mock_versions):
        # Setup mocks
        prompt_data = MagicMock()
        prompt_data.id = "test-prompt"

        mock_get_data.return_value = PromptData(
            id="test-prompt",
            app_id="test-app",
            app_name="Test App",
            is_undeployed=False,
            major_versions=[
                {"version": "1", "params": {}, "templates": [], "tools": []},
                {"version": "2", "params": {}, "templates": [], "tools": []},
            ],
            undeployed_data=None,
        )

        mock_versions.return_value = ["version1_code", "version2_code"]
        mock_factory.return_value = "factory_class_code"

        # Test prompt implementation generation for deployed prompts
        result = generate_prompt_implementations(
            app_id="test-app", app_name="Test App", prompt_data=prompt_data, api_client=None
        )

        # Check factory was called with the correct versions
        mock_factory.assert_called_once_with(title_case_id="TestPrompt", major_versions=["1", "2"])

        # Check version implementations was called for each version
        assert mock_versions.call_count == 2

        # Check the result
        assert "version1_code" in result
        assert "version2_code" in result
        assert "factory_class_code" in result

    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_version_implementations")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_factory_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.generate_manager_class_code")
    @patch("autoblocks._impl.prompts.v2.discovery.prompts.get_prompt_data")
    def test_generate_prompt_implementations_undeployed(self, mock_get_data, mock_manager, mock_factory, mock_versions):
        # Setup mocks
        prompt_data = MagicMock()
        prompt_data.id = "test-prompt"

        mock_get_data.return_value = PromptData(
            id="test-prompt",
            app_id="test-app",
            app_name="Test App",
            is_undeployed=True,
            major_versions=[],
            undeployed_data={"params": {}, "templates": [], "tools": []},
        )

        mock_versions.return_value = ["undeployed_version_code"]
        mock_factory.return_value = "undeployed_factory_code"

        # Test prompt implementation generation for undeployed prompts
        result = generate_prompt_implementations(
            app_id="test-app", app_name="Test App", prompt_data=prompt_data, api_client=None
        )

        # Check factory was called with is_undeployed=True
        mock_factory.assert_called_once_with(title_case_id="TestPrompt", major_versions=[], is_undeployed=True)

        # Check the result
        assert "undeployed_version_code" in result
        assert "undeployed_factory_code" in result
