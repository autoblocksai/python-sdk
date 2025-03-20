import os
from unittest import mock

from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.prompts.v2.autogenerate import write_generated_code_for_config
from autoblocks._impl.prompts.v2.models import AutogeneratePromptConfig, AutogeneratePromptsConfig

from tests.autoblocks.v2.test_api_client import TEST_APP_ID, MOCK_PROMPT_BASIC_V1
from tests.autoblocks.v2.test_manager import MOCK_PROMPT_BASIC_V2

MOCK_PROMPT_BASIC_UNDEPLOYED = {
    "id": "prompt-basic",
    "appId": TEST_APP_ID,
    "majorVersions": [
        {
            "majorVersion": "dangerously-use-undeployed",
            "minorVersions": ["latest"],
            "templates": [
                {
                    "id": "template-undeployed",
                    "template": "This is an undeployed template with {{ variable }}.",
                },
            ],
            "params": {
                "model": "gpt-4-turbo",
                "temperature": 0.8,
            },
            "toolsParams": []
        }
    ]
}


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_V2_API_KEY": "mock-v2-api-key",
    },
)
class TestAutogenerate:
    """Tests for V2 prompt autogeneration."""
    
    def test_generate_v1_prompt(self, httpx_mock, tmp_path):
        """Test generating code for a V1 prompt."""

        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V1,
        )
        
        
        outfile = tmp_path / "test_v2_autogen_v1.py"
        
        
        config = AutogeneratePromptsConfig(
            outfile=str(outfile),
            app_id=TEST_APP_ID,
            prompts=[
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    major_version="1",
                ),
            ],
        )
        
        write_generated_code_for_config(config)
        
        assert outfile.exists()
        
        content = outfile.read_text()
        assert "class PromptBasicParams(FrozenModel):" in content
        assert "frequency_penalty: Union[float, int]" in content
        assert "model: str" in content
        assert "class PromptBasicTemplateRenderer(TemplateRenderer):" in content
        assert '"name": "name"' in content
        assert '"weather": "weather"' in content
        assert "def template_a(" in content
        assert "def template_b(" in content
        assert f'__app_id__ = "{TEST_APP_ID}"' in content
        assert '__prompt_id__ = "prompt-basic"' in content
        assert '__prompt_major_version__ = "1"' in content
    
    def test_generate_v2_prompt(self, httpx_mock, tmp_path):
        """Test generating code for a V2 prompt."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/2/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V2,
        )
        
        
        outfile = tmp_path / "test_v2_autogen_v2.py"
        
        
        config = AutogeneratePromptsConfig(
            outfile=str(outfile),
            app_id=TEST_APP_ID,
            prompts=[
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    major_version="2",
                ),
            ],
        )
        
        write_generated_code_for_config(config)
        
        
        assert outfile.exists()
        
        
        content = outfile.read_text()
        assert "class PromptBasicParams(FrozenModel):" in content
        assert "model: str" in content
        assert "seed: Union[float, int]" in content
        assert "top_k: Union[float, int]" in content
        assert "class PromptBasicTemplateRenderer(TemplateRenderer):" in content
        assert '"first_name": "first_name"' in content
        assert "def template_c(" in content
        assert f'__app_id__ = "{TEST_APP_ID}"' in content
        assert '__prompt_id__ = "prompt-basic"' in content
        assert '__prompt_major_version__ = "2"' in content
    
    def test_generate_undeployed_prompt(self, httpx_mock, tmp_path):
        """Test generating code for an undeployed prompt."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/dangerously-use-undeployed/minor/latest",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_UNDEPLOYED,
        )
        
        
        outfile = tmp_path / "test_v2_autogen_undeployed.py"
        
        
        config = AutogeneratePromptsConfig(
            outfile=str(outfile),
            app_id=TEST_APP_ID,
            prompts=[
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    dangerously_use_undeployed_revision="latest",
                ),
            ],
        )
        
        write_generated_code_for_config(config)
        
        
        assert outfile.exists()
        
        
        content = outfile.read_text()
        assert "class PromptBasicParams(FrozenModel):" in content
        assert "model: str" in content
        assert "temperature: Union[float, int]" in content
        assert "class PromptBasicTemplateRenderer(TemplateRenderer):" in content
        assert "def template_undeployed(" in content
        assert f'__app_id__ = "{TEST_APP_ID}"' in content
        assert '__prompt_id__ = "prompt-basic"' in content
        assert '__prompt_major_version__ = "dangerously-use-undeployed"' in content
    
    def test_generate_multiple_prompts(self, httpx_mock, tmp_path):
        """Test generating code for multiple prompts."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V1,
        )
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/2/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V2,
        )
        
        
        outfile = tmp_path / "test_v2_autogen_multiple.py"
        
        
        config = AutogeneratePromptsConfig(
            outfile=str(outfile),
            app_id=TEST_APP_ID,
            prompts=[
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    major_version="1",
                ),
                AutogeneratePromptConfig(
                    id="prompt-basic",
                    major_version="2",
                ),
            ],
        )
        
        write_generated_code_for_config(config)
        
        
        assert outfile.exists()
        
        
        content = outfile.read_text()
        assert "class PromptBasicParams(FrozenModel):" in content  
        assert "frequency_penalty: Union[float, int]" in content  
        assert "seed: Union[float, int]" in content  
        assert "def template_a(" in content  
        assert "def template_c(" in content  