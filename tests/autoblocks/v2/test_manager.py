import os
from unittest import mock
from typing import Dict, Any, List

from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.prompts.v2.manager import AutoblocksPromptManager

from tests.autoblocks.v2.test_api_client import MOCK_PROMPT_BASIC_V1, TEST_APP_ID



MOCK_PROMPT_BASIC_V2 = {
    "id": "prompt-basic",
    "appId": TEST_APP_ID,
    "majorVersions": [
        {
            "majorVersion": "2",
            "minorVersions": ["0", "1", "latest"],
            "templates": [
                {
                    "id": "template-c",
                    "template": "Hello, {{ first_name }}!",
                },
            ],
            "params": {
                "model": "gpt-4",
                "seed": 4096,
                "topK": 10,
            },
            "toolsParams": []
        }
    ]
}


class TestPromptBasicParamsV1:
    """Pydantic model to match the generated params class for testing."""
    frequency_penalty: float = 0
    max_tokens: int = 256
    model: str = "gpt-4"
    presence_penalty: float = 0.3
    stop_sequences: List = []
    temperature: float = 0.7
    top_p: float = 1


class TestPromptBasicParamsV2:
    """Pydantic model to match the generated params class for testing."""
    model: str = "gpt-4"
    seed: int = 4096
    top_k: int = 10



class MockTemplateRenderer:
    def __init__(self, templates):
        self._templates = {t["id"]: t["template"] for t in templates}
        
    def template_a(self, *, name: str, weather: str) -> str:
        return self._templates["template-a"].replace("{{ name }}", name).replace("{{ weather }}", weather)
        
    def template_b(self, *, name: str) -> str:
        return self._templates["template-b"].replace("{{ name }}", name)

    def template_c(self, *, first_name: str) -> str:
        return self._templates["template-c"].replace("{{ first_name }}", first_name)


class MockToolRenderer:
    def __init__(self, tools):
        self._tools = tools


class MockPromptExecutionContext:
    def __init__(self, prompt, major_version):
        self._prompt = prompt
        self._major_version = major_version
        self.params = TestPromptBasicParamsV1() if major_version.major_version == "1" else TestPromptBasicParamsV2()
        self.render_template = MockTemplateRenderer(major_version.templates)
        self.render_tool = MockToolRenderer(major_version.tools_params or [])
        
    def track(self) -> Dict[str, Any]:
        return {
            "id": self._prompt.id,
            "appId": self._prompt.app_id,
            "majorVersion": self._major_version.major_version,
        }


class MockPromptManager(AutoblocksPromptManager):
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
class TestPromptManager:
    """Tests for the V2 prompt manager."""
    
    def test_init_and_fetch(self, httpx_mock):
        """Test manager initialization and prompt fetching."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V1,
        )
        
        manager = MockPromptManager(minor_version="0")
        
        
        assert "0" in manager._minor_version_to_prompt
        assert manager._minor_version_to_prompt["0"].id == "prompt-basic"
    
    def test_exec_and_render(self, httpx_mock):
        """Test executing a prompt and rendering templates."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V1,
        )
        
        manager = MockPromptManager(minor_version="0")
        
        with manager.exec() as ctx:
            
            assert ctx.params.model == "gpt-4"
            assert ctx.params.temperature == 0.7
            
            
            rendered = ctx.render_template.template_a(name="John", weather="sunny")
            assert rendered == "Hello, John! The weather is sunny today."
            
            
            tracking = ctx.track()
            assert tracking["id"] == "prompt-basic"
            assert tracking["appId"] == TEST_APP_ID
    
    def test_different_major_version(self, httpx_mock):
        """Test using a different major version."""
        
        class CustomMajorVersionManager(MockPromptManager):
            __prompt_major_version__ = "2"
        
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/2/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V2,
        )
        
        manager = CustomMajorVersionManager(minor_version="0")
        
        with manager.exec() as ctx:
            
            assert ctx.params.model == "gpt-4"
            assert ctx.params.seed == 4096
            assert ctx.params.top_k == 10
            
            
            rendered = ctx.render_template.template_c(first_name="Alice")
            assert rendered == "Hello, Alice!" 