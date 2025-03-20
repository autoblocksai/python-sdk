import os
from unittest import mock

import pytest

from autoblocks._impl.api.v2.client import AutoblocksAPIClient
from autoblocks._impl.config.constants import V2_API_ENDPOINT

TEST_APP_ID = "jqg74mpzzovssq38j055yien"

MOCK_PROMPT_BASIC_V1 = {
    "id": "prompt-basic",
    "appId": TEST_APP_ID,
    "majorVersions": [
        {
            "majorVersion": "1",
            "minorVersions": ["0", "latest"],
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
                {
                    "id": "template-b",
                    "template": "Hello, {{ name }}!",
                },
            ],
            "params": {
                "frequencyPenalty": 0,
                "maxTokens": 256,
                "model": "gpt-4",
                "presencePenalty": 0.3,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 1,
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
class TestAutoblocksV2APIClient:
    """Tests for the V2 API client."""
    
    def test_init_with_env_var(self):
        """Test client initialization with environment variable."""
        client = AutoblocksAPIClient()
        assert client._client.headers["Authorization"] == "Bearer mock-v2-api-key"
        assert client._client.base_url == V2_API_ENDPOINT
    
    def test_init_with_api_key(self):
        """Test client initialization with explicit API key."""
        client = AutoblocksAPIClient(api_key="explicit-key")
        assert client._client.headers["Authorization"] == "Bearer explicit-key"
    
    def test_init_no_api_key(self):
        """Test client initialization with no API key raises error."""
        with mock.patch.dict(os.environ, {"AUTOBLOCKS_V2_API_KEY": ""}):
            with pytest.raises(ValueError, match="You must provide an api_key"):
                AutoblocksAPIClient()
    
    def test_get_prompt(self, httpx_mock):
        """Test getting a prompt."""
    
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
            json=MOCK_PROMPT_BASIC_V1,
        )
        
        client = AutoblocksAPIClient()
        prompt = client.get_prompt(
            app_id=TEST_APP_ID,
            prompt_id="prompt-basic",
            major_version="1",
            minor_version="0",
        )
        
        assert prompt.id == "prompt-basic"
        assert prompt.app_id == TEST_APP_ID
        assert len(prompt.major_versions) == 1
        assert prompt.major_versions[0].major_version == "1"
        assert len(prompt.major_versions[0].templates) == 2
        assert prompt.major_versions[0].templates[0].id == "template-a" 