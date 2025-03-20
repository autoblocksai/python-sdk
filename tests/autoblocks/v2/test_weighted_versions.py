import os
from unittest import mock

from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.prompts.models import WeightedMinorVersion
from autoblocks._impl.prompts.v2.manager import AutoblocksPromptManager

from tests.autoblocks.v2.test_api_client import TEST_APP_ID
from tests.autoblocks.v2.test_manager import MockPromptExecutionContext, MOCK_PROMPT_BASIC_V1


class WeightedMockManager(AutoblocksPromptManager):
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
class TestWeightedVersions:
    """Tests for V2 prompt manager with weighted minor versions."""
    
    def test_weighted_version_selection(self, httpx_mock, monkeypatch):
        """Test selecting minor versions based on weights."""
        
        for minor_version in ["0", "1", "2"]:
            
            response = MOCK_PROMPT_BASIC_V1.copy()
            response["majorVersions"][0]["minorVersions"] = ["0", "1", "2"]
            
            response["majorVersions"][0]["params"]["version_specific"] = f"version-{minor_version}"
            
            httpx_mock.add_response(
                url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/{minor_version}",
                method="GET",
                json=response,
                match_headers={"Authorization": "Bearer mock-v2-api-key"},
            )
        
        
        weighted_versions = [
            WeightedMinorVersion(version="0", weight=1.0),
            WeightedMinorVersion(version="1", weight=2.0),
            WeightedMinorVersion(version="2", weight=3.0),
        ]
        
        
        counts = {"0": 0, "1": 0, "2": 0}
        
        
        for _ in range(100):
            manager = WeightedMockManager(minor_version=weighted_versions)
            
            
            with manager.exec() as ctx:
                
                version_specific = ctx._major_version.params.get("version_specific", "")
                if "version-0" in version_specific:
                    counts["0"] += 1
                elif "version-1" in version_specific:
                    counts["1"] += 1
                elif "version-2" in version_specific:
                    counts["2"] += 1
        
        
        assert counts["2"] > counts["1"]
        assert counts["1"] > counts["0"]
        
        
        total = sum(counts.values())
        weights_sum = sum(v.weight for v in weighted_versions)
        
        
        
        
        expected_0 = (weighted_versions[0].weight / weights_sum) * total
        expected_1 = (weighted_versions[1].weight / weights_sum) * total
        expected_2 = (weighted_versions[2].weight / weights_sum) * total
        
        
        assert 0.7 * expected_0 <= counts["0"] <= 1.3 * expected_0
        assert 0.7 * expected_1 <= counts["1"] <= 1.3 * expected_1
        assert 0.7 * expected_2 <= counts["2"] <= 1.3 * expected_2
    
    def test_single_version_string(self, httpx_mock):
        """Test using a single version string instead of weighted versions."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/specific-version",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        manager = WeightedMockManager(minor_version="specific-version")
        
        
        with manager.exec() as ctx:
            assert "specific-version" in manager._minor_version_to_prompt
    
    def test_latest_version(self, httpx_mock):
        """Test using 'latest' as the version string."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/latest",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        manager = WeightedMockManager(minor_version="latest")
        
        
        with manager.exec() as ctx:
            assert "latest" in manager._minor_version_to_prompt 