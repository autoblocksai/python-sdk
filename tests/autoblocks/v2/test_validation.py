import os
from unittest import mock

import pytest
import httpx

from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.prompts.v2.manager import AutoblocksPromptManager
from autoblocks._impl.prompts.v2.models import AutogeneratePromptConfig, AutogeneratePromptsConfig
from autoblocks._impl.prompts.v2.autogenerate import write_generated_code_for_config

from tests.autoblocks.v2.test_api_client import TEST_APP_ID
from tests.autoblocks.v2.test_manager import MockPromptExecutionContext, MOCK_PROMPT_BASIC_V1


class ValidationMockManager(AutoblocksPromptManager):
    __prompt_id__ = "prompt-basic"
    __app_id__ = TEST_APP_ID
    __prompt_major_version__ = "1"
    __execution_context_class__ = MockPromptExecutionContext


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-v2-api-key",
    },
)
class TestValidation:
    """Tests for V2 validation and error handling."""
    
    def test_api_error_handling(self, httpx_mock):
        """Test handling of API errors."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            status_code=404,
            json={"error": "Prompt not found"},
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        with pytest.raises(httpx.HTTPStatusError):
            ValidationMockManager(minor_version="0")
    
    def test_invalid_major_version(self, httpx_mock):
        """Test handling of invalid major version."""
        
        modified_prompt = MOCK_PROMPT_BASIC_V1.copy()
        modified_prompt["majorVersions"][0]["majorVersion"] = "2"  
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=modified_prompt,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        with pytest.raises(ValueError, match="not found"):
            ValidationMockManager(minor_version="0")
    
    def test_autogenerate_validation(self, httpx_mock, tmp_path):
        """Test validation in the autogeneration process."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/non-existent/major/1/minor/0",
            method="GET",
            status_code=404,
            json={"error": "Prompt not found"},
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        config = AutogeneratePromptsConfig(
            outfile=str(tmp_path / "test_validation.py"),
            app_id=TEST_APP_ID,
            prompts=[
                
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    major_version="1",
                ),
                
                AutogeneratePromptConfig(
                    id="non-existent",
                    major_version="1",
                ),
            ],
        )
        
        
        try:
            write_generated_code_for_config(config)
            output_file = tmp_path / "test_validation.py"
            assert output_file.exists()
            
            
            content = output_file.read_text()
            assert "class PromptBasicParams" in content
            assert "class PromptBasicTemplateRenderer" in content
        except Exception as e:
            
            
            output_file = tmp_path / "test_validation.py"
            assert output_file.exists()
            
            
            content = output_file.read_text()
            assert "class PromptBasicParams" in content
    
    def test_invalid_config(self):
        """Test validation of the config model."""
        
        with pytest.raises(ValueError):
            AutogeneratePromptsConfig(
                outfile="test.py",
                
                prompts=[
                    AutogeneratePromptConfig(
                        id="prompt-basic",
                        major_version="1",
                    ),
                ],
            )
        
        
        with pytest.raises(ValueError):
            AutogeneratePromptsConfig(
                outfile="test.py",
                app_id=TEST_APP_ID,
                prompts=[
                    AutogeneratePromptConfig(
                        id="prompt-basic",
                        major_version="1",
                        dangerously_use_undeployed_revision="latest",  
                    ),
                ],
            )
        
        
        with pytest.raises(ValueError):
            AutogeneratePromptsConfig(
                outfile="test.py",
                app_id=TEST_APP_ID,
                prompts=[
                    AutogeneratePromptConfig(
                        id="prompt-basic",
                        
                    ),
                ],
            ) 