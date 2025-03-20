import os
from pathlib import Path
from unittest import mock

import yaml
from click.testing import CliRunner

from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.prompts.cli.main import prompts

from tests.autoblocks.v2.test_api_client import TEST_APP_ID
from tests.autoblocks.v2.test_manager import MOCK_PROMPT_BASIC_V1


def create_test_config_file(tmpdir: Path, with_v2: bool = True) -> Path:
    """Create a test config file with V1 and optionally V2 configurations."""
    config_data = {
        "autogenerate": {
            "prompts": {
                "outfile": str(tmpdir / "v1_prompts.py"),
                "prompts": [
                    {
                        "id": "prompt-basic",
                        "major_version": "1",
                    },
                ],
            },
        },
    }
    
    if with_v2:
        config_data["autogenerate_v2"] = {
            "prompts": {
                "outfile": str(tmpdir / "v2_prompts.py"),
                "app_id": TEST_APP_ID,
                "prompts": [
                    {
                        "id": "prompt-basic",
                        "major_version": "1",
                    },
                ],
            },
        }
    
    config_file = tmpdir / ".autoblocks.yml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    return config_file


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_V2_API_KEY": "mock-v2-api-key",
    },
)
class TestCLI:
    """Tests for the prompts CLI with V2 support."""
    
    def test_generate_v2_only(self, httpx_mock, tmp_path):
        """Test the generate command with only V2 API."""
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        config_file = create_test_config_file(tmp_path)
        
        
        runner = CliRunner()
        result = runner.invoke(
            prompts, 
            ["generate", "--config-path", str(config_file), "--api-version", "v2"]
        )
        
        
        assert result.exit_code == 0
        assert "Successfully generated V2 prompts" in result.output
        
        
        output_file = tmp_path / "v2_prompts.py"
        assert output_file.exists()
    
    def test_generate_both_apis(self, httpx_mock, tmp_path):
        """Test the generate command with both V1 and V2 APIs."""
        
        httpx_mock.add_response(
            url="https://api.autoblocks.ai/prompts/prompt-basic/major/1/minor/latest",
            method="GET",
            json={
                "id": "prompt-basic",
                "params": {
                    "params": {
                        "model": "gpt-4",
                        "temperature": 0.7,
                    },
                },
                "templates": [
                    {
                        "id": "template-a",
                        "template": "Hello, {{ name }}!",
                    },
                ],
                "version": "1.0",
                "revisionId": "mock-revision-id",
            },
            match_headers={"Authorization": "Bearer mock-api-key"},
        )
        
        
        httpx_mock.add_response(
            url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
            method="GET",
            json=MOCK_PROMPT_BASIC_V1,
            match_headers={"Authorization": "Bearer mock-v2-api-key"},
        )
        
        
        config_file = create_test_config_file(tmp_path)
        
        
        runner = CliRunner()
        result = runner.invoke(
            prompts, 
            ["generate", "--config-path", str(config_file), "--api-version", "all"]
        )
        
        
        assert result.exit_code == 0
        assert "Successfully generated V1 prompts" in result.output
        assert "Successfully generated V2 prompts" in result.output
        
        
        v1_output_file = tmp_path / "v1_prompts.py"
        v2_output_file = tmp_path / "v2_prompts.py"
        assert v1_output_file.exists()
        assert v2_output_file.exists()
    
    def test_default_config_path(self, httpx_mock, tmp_path, monkeypatch):
        """Test using the default config path."""
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            
            create_test_config_file(tmp_path)
            
            
            httpx_mock.add_response(
                url=f"{V2_API_ENDPOINT}/apps/{TEST_APP_ID}/prompts/prompt-basic/major/1/minor/0",
                method="GET",
                json=MOCK_PROMPT_BASIC_V1,
                match_headers={"Authorization": "Bearer mock-v2-api-key"},
            )
            
            
            runner = CliRunner()
            result = runner.invoke(
                prompts, 
                ["generate", "--api-version", "v2"]
            )
            
            
            assert result.exit_code == 0
            assert "Successfully generated V2 prompts" in result.output
            
            
            output_file = tmp_path / "v2_prompts.py"
            assert output_file.exists()
        finally:
            
            os.chdir(old_cwd)
    
    def test_missing_api_key(self, tmp_path):
        """Test error when API key is missing."""
        
        config_file = create_test_config_file(tmp_path)
        
        
        with mock.patch.dict(os.environ, {"AUTOBLOCKS_V2_API_KEY": ""}):
            runner = CliRunner()
            result = runner.invoke(
                prompts, 
                ["generate", "--config-path", str(config_file), "--api-version", "v2"]
            )
            
            
            assert result.exit_code != 0
            assert "You must set the AUTOBLOCKS_V2_API_KEY environment variable" in result.output
    
    def test_missing_v2_config(self, tmp_path):
        """Test warning when V2 config is missing but V2 API version is specified."""
        
        config_file = create_test_config_file(tmp_path, with_v2=False)
        
        
        runner = CliRunner()
        result = runner.invoke(
            prompts, 
            ["generate", "--config-path", str(config_file), "--api-version", "all"]
        )
        
        
        assert result.exit_code == 0
        assert "Successfully generated V1 prompts" in result.output
        
        assert "Successfully generated V2 prompts" not in result.output 