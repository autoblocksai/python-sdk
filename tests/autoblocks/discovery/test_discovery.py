from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from autoblocks._impl.prompts.v2.discovery import PromptModulesGenerator
from autoblocks._impl.prompts.v2.discovery import generate_all_prompt_modules


class TestPromptModulesGenerator:
    @patch("autoblocks._impl.prompts.v2.discovery.PromptsAPIClient")
    def test_generator_initialization(self, mock_client):
        """Test the initialization of the generator class."""
        # Create the generator
        generator = PromptModulesGenerator(api_key="test_key", output_dir="/test/output")

        # Check client initialization
        mock_client.assert_called_once_with(api_key="test_key")

        # Check attributes
        assert generator.api_key == "test_key"
        assert generator.output_dir == "/test/output"
        assert generator.client == mock_client.return_value

    def test_group_prompts_by_app(self):
        """Test grouping prompts by app."""
        generator = PromptModulesGenerator(api_key="test_key", output_dir="/test/output")

        # Create mock prompts
        prompt1 = MagicMock()
        prompt1.app_id = "app1"
        prompt1.app_name = "App One"

        prompt2 = MagicMock()
        prompt2.app_id = "app1"
        prompt2.app_name = "App One"

        prompt3 = MagicMock()
        prompt3.app_id = "app2"
        prompt3.app_name = "App Two"

        # Group the prompts
        result = generator._group_prompts_by_app([prompt1, prompt2, prompt3])

        # Check the result
        assert len(result) == 2
        assert result["app1"]["app_name"] == "App One"
        assert len(result["app1"]["prompts"]) == 2
        assert result["app2"]["app_name"] == "App Two"
        assert len(result["app2"]["prompts"]) == 1


class TestGenerateAllPromptModules:
    @patch("autoblocks._impl.prompts.v2.discovery.PromptModulesGenerator")
    def test_generate_all_prompt_modules(self, mock_generator_class):
        """Test the main entry point function."""
        # Setup mock
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        # Call the function
        generate_all_prompt_modules(api_key="test_key", output_dir="/test/output")

        # Check generator initialization - use positional args since that's what's being used
        mock_generator_class.assert_called_once_with("test_key", "/test/output")

        # Check generate call
        mock_generator.generate.assert_called_once()

    def test_generate_all_prompt_modules_missing_output_dir(self):
        """Test error handling when output dir is missing."""
        with pytest.raises(ValueError) as excinfo:
            generate_all_prompt_modules(api_key="test_key")

        assert "Output directory must be specified" in str(excinfo.value)
