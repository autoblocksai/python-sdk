import asyncio
import os
from unittest import mock

import pytest

from autoblocks._impl.config.constants import V2_API_ENDPOINT, REVISION_LATEST
from autoblocks._impl.prompts.v2.manager import AutoblocksPromptManager

from tests.autoblocks.v2.test_api_client import TEST_APP_ID
from tests.autoblocks.v2.test_manager import MockPromptExecutionContext, MOCK_PROMPT_BASIC_V1


class RefreshMockManager(AutoblocksPromptManager):
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
class TestRefresh:
    """Tests for V2 prompt manager refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_latest_prompt(self, httpx_mock):
        """Test that 'latest' prompts are periodically refreshed."""
        
        initial_prompt = MOCK_PROMPT_BASIC_V1.copy()
        initial_prompt["majorVersions"][0]["params"]["version"] = "initial"
        
        
        updated_prompt = MOCK_PROMPT_BASIC_V1.copy()
        updated_prompt["majorVersions"][0]["params"]["version"] = "updated"
        
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/{REVISION_LATEST}",
            method="GET",
            json=initial_prompt,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        refresh_interval = 0.1  
        manager = RefreshMockManager(
            minor_version=REVISION_LATEST,
            refresh_interval=asyncio.timedelta(seconds=refresh_interval),
        )
        
        
        with manager.exec() as ctx:
            version_param = ctx._major_version.params.get("version")
            assert version_param == "initial"
        
        
        httpx_mock.reset()
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/{REVISION_LATEST}",
            method="GET",
            json=updated_prompt,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        await asyncio.sleep(refresh_interval * 2)
        
        
        with manager.exec() as ctx:
            version_param = ctx._major_version.params.get("version")
            assert version_param == "updated"
    
    def test_non_latest_no_refresh(self, httpx_mock):
        """Test that non-'latest' prompts are not refreshed."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        manager = RefreshMockManager(minor_version="0")
        
        
        assert "0" in manager._minor_version_to_prompt
        
        
        httpx_mock.reset()
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        with manager.exec() as ctx:
            pass
        
        
        requests = httpx_mock.get_requests()
        assert len(requests) == 0
    
    @pytest.mark.asyncio
    async def test_refresh_error_handling(self, httpx_mock, caplog):
        """Test that refresh errors are handled properly and don't crash the application."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/{REVISION_LATEST}",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        refresh_interval = 0.1  
        manager = RefreshMockManager(
            minor_version=REVISION_LATEST,
            refresh_interval=asyncio.timedelta(seconds=refresh_interval),
        )
        
        
        assert REVISION_LATEST in manager._minor_version_to_prompt
        
        
        httpx_mock.reset()
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/{REVISION_LATEST}",
            method="GET",
            status_code=500,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        await asyncio.sleep(refresh_interval * 2)
        
        
        assert any("Error refreshing prompt" in record.message for record in caplog.records)
        
        
        with manager.exec() as ctx:
            
            assert ctx._prompt.id == "prompt-basic" 