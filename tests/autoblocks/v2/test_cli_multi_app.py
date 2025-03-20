import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest import mock

import yaml
from click.testing import CliRunner

from autoblocks._impl.prompts.cli import main


MOCK_PROMPT_V2 = {
    "id": "test-prompt",
    "majorVersion": "1",
    "minorVersion": "0",
    "name": "Test Prompt",
    "description": "A test prompt for CLI testing",
    "template": "This is a test prompt with parameter {{ param1 }}",
    "parameters": [
        {
            "name": "param1",
            "type": "string",
            "description": "Test parameter",
            "required": True
        }
    ]
}


def create_test_config(config_data: Dict[str, Any]) -> Path:
    """Create a temporary YAML configuration file for testing."""
    temp_dir = tempfile.gettempdir()
    config_path = Path(temp_dir) / "test_config.yaml"
    
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    
    return config_path


def remove_files(file_paths: List[Path]):
    """Remove test files."""
    for path in file_paths:
        if path.exists():
            os.remove(path)


class TestCliMultiApp:
    """Tests for the CLI with multi-app prompts generation."""
    
    def setup_method(self):
        self.temp_dir = tempfile.gettempdir()
        self.runner = CliRunner()
    
    def test_generate_single_app(self):
        """Test generating a single app's prompts using the CLI."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            "outfile": "app1_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                        {
                            "app_id": "app_id_2",
                            "outfile": "app2_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        app1_output = Path(self.temp_dir) / "app1_prompts.py"
        app2_output = Path(self.temp_dir) / "app2_prompts.py"
        
        try:
            with mock.patch.dict(os.environ, {"AUTOBLOCKS_API_KEY_V2": "test-key"}):
                with mock.patch("httpx.get") as mock_get:
                    mock_response = mock.MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = MOCK_PROMPT_V2
                    mock_get.return_value = mock_response
                    
                    # Run CLI command for app_id_1 only
                    result = self.runner.invoke(
                        main.prompts,
                        [
                            "--config", str(config_path),
                            "--app-id", "app_id_1",
                            "--output-dir", self.temp_dir
                        ]
                    )
                    
                    # Verify results
                    assert result.exit_code == 0
                    assert "Generated V2 prompts for app app_id_1" in result.output
                    assert "Generated V2 prompts for app app_id_2" not in result.output
                    
                    assert app1_output.exists()
                    assert not app2_output.exists()
                    
                    with open(app1_output, "r") as f:
                        content = f.read()
                        assert "TestPromptPromptManager" in content
                        assert "app_id='app_id_1'" in content
        finally:
            remove_files([config_path, app1_output, app2_output])
    
    def test_generate_all_apps(self):
        """Test generating prompts for all apps."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            "outfile": "app1_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                        {
                            "app_id": "app_id_2",
                            "outfile": "app2_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        app1_output = Path(self.temp_dir) / "app1_prompts.py"
        app2_output = Path(self.temp_dir) / "app2_prompts.py"
        
        try:
            with mock.patch.dict(os.environ, {"AUTOBLOCKS_API_KEY_V2": "test-key"}):
                with mock.patch("httpx.get") as mock_get:
                    mock_response = mock.MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = MOCK_PROMPT_V2
                    mock_get.return_value = mock_response
                    
                    # Run CLI command without app-id to generate all
                    result = self.runner.invoke(
                        main.prompts,
                        [
                            "--config", str(config_path),
                            "--output-dir", self.temp_dir
                        ]
                    )
                    
                    # Verify results
                    assert result.exit_code == 0
                    assert "Generated V2 prompts for app app_id_1" in result.output
                    assert "Generated V2 prompts for app app_id_2" in result.output
                    
                    assert app1_output.exists()
                    assert app2_output.exists()
                    
                    # Check app1 output
                    with open(app1_output, "r") as f:
                        content = f.read()
                        assert "TestPromptPromptManager" in content
                        assert "app_id='app_id_1'" in content
                    
                    # Check app2 output
                    with open(app2_output, "r") as f:
                        content = f.read()
                        assert "TestPromptPromptManager" in content
                        assert "app_id='app_id_2'" in content
        finally:
            remove_files([config_path, app1_output, app2_output])
    
    def test_mixed_v1_v2_generation(self):
        """Test generating prompts for both V1 and V2 apps."""
        config_data = {
            "autogenerate": {
                "prompts": {
                    "outfile": "v1_prompts.py",
                    "prompts": [
                        {
                            "id": "legacy-prompt",
                            "major_version": "1",
                        },
                    ],
                },
            },
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            "outfile": "app1_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        v1_output = Path(self.temp_dir) / "v1_prompts.py"
        app1_output = Path(self.temp_dir) / "app1_prompts.py"
        
        try:
            with mock.patch.dict(os.environ, {
                "AUTOBLOCKS_API_KEY": "test-key-v1",
                "AUTOBLOCKS_API_KEY_V2": "test-key-v2"
            }):
                with mock.patch("httpx.get") as mock_get:
                    mock_response = mock.MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = MOCK_PROMPT_V2
                    mock_get.return_value = mock_response
                    
                    # Run CLI command to generate all prompts
                    result = self.runner.invoke(
                        main.prompts,
                        [
                            "--config", str(config_path),
                            "--output-dir", self.temp_dir
                        ]
                    )
                    
                    # Verify results
                    assert result.exit_code == 0
                    assert "Generated V1 prompts" in result.output
                    assert "Generated V2 prompts for app app_id_1" in result.output
                    
                    assert v1_output.exists()
                    assert app1_output.exists()
                    
                    # Check V1 output
                    with open(v1_output, "r") as f:
                        content = f.read()
                        assert "LegacyPrompt" in content
                    
                    # Check V2 output
                    with open(app1_output, "r") as f:
                        content = f.read()
                        assert "TestPromptPromptManager" in content
                        assert "app_id='app_id_1'" in content
        finally:
            remove_files([config_path, v1_output, app1_output])
    
    def test_app_id_not_found(self):
        """Test error handling when specified app ID is not found."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            "outfile": "app1_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        
        try:
            with mock.patch.dict(os.environ, {"AUTOBLOCKS_API_KEY_V2": "test-key"}):
                # Run CLI command with non-existent app-id
                result = self.runner.invoke(
                    main.prompts,
                    [
                        "--config", str(config_path),
                        "--app-id", "non_existent_app",
                        "--output-dir", self.temp_dir
                    ]
                )
                
                # Verify error
                assert result.exit_code != 0
                assert "App ID 'non_existent_app' not found in configuration" in result.output
        finally:
            remove_files([config_path])
    
    def test_missing_v2_api_key(self):
        """Test error handling when V2 API key is missing."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            "outfile": "app1_prompts.py",
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        
        try:
            # No V2 API key in environment
            with mock.patch.dict(os.environ, {}, clear=True):
                result = self.runner.invoke(
                    main.prompts,
                    [
                        "--config", str(config_path),
                        "--output-dir", self.temp_dir
                    ]
                )
                
                # Verify error
                assert result.exit_code != 0
                assert "AUTOBLOCKS_API_KEY_V2 environment variable must be set" in result.output
        finally:
            remove_files([config_path])
    
    def test_default_outfile_fallback(self):
        """Test that app configurations without outfile use the default outfile."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "default_prompts.py",
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            # No outfile specified, should use default
                            "prompts": [
                                {
                                    "id": "test-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        default_output = Path(self.temp_dir) / "default_prompts.py"
        
        try:
            with mock.patch.dict(os.environ, {"AUTOBLOCKS_API_KEY_V2": "test-key"}):
                with mock.patch("httpx.get") as mock_get:
                    mock_response = mock.MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = MOCK_PROMPT_V2
                    mock_get.return_value = mock_response
                    
                    # Run CLI command
                    result = self.runner.invoke(
                        main.prompts,
                        [
                            "--config", str(config_path),
                            "--output-dir", self.temp_dir
                        ]
                    )
                    
                    # Verify results
                    assert result.exit_code == 0
                    assert "Generated V2 prompts for app app_id_1" in result.output
                    assert default_output.exists()
                    
                    with open(default_output, "r") as f:
                        content = f.read()
                        assert "TestPromptPromptManager" in content
                        assert "app_id='app_id_1'" in content
        finally:
            remove_files([config_path, default_output]) 