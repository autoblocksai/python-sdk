import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml

from autoblocks._impl.prompts.cli.models import YamlConfig


def create_test_config(config_data: Dict[str, Any]) -> Path:
    """Create a test YAML configuration file."""
    temp_dir = tempfile.gettempdir()
    config_path = Path(temp_dir) / "test_config.yaml"
    
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    
    return config_path


class TestMultiAppConfig:
    """Tests for multi-app configuration support."""
    
    def test_legacy_v1_config(self):
        """Test that legacy V1 configurations still work."""
        config_data = {
            "autogenerate": {
                "prompts": {
                    "outfile": "v1_prompts.py",
                    "prompts": [
                        {
                            "id": "test-prompt",
                            "major_version": "1",
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        try:
            yaml_config = YamlConfig.model_validate(config_data)
            
            # Check V1 config is loaded
            assert yaml_config.autogenerate is not None
            assert yaml_config.autogenerate.prompts.outfile == "v1_prompts.py"
            assert len(yaml_config.autogenerate.prompts.prompts) == 1
            
            # Check no V2 configs
            v2_configs = yaml_config.get_v2_configs()
            assert len(v2_configs) == 0
        finally:
            os.remove(config_path)
    
    def test_legacy_v2_config(self):
        """Test that legacy single-app V2 configurations still work."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    "outfile": "v2_prompts.py",
                    "app_id": "app_id_1",
                    "prompts": [
                        {
                            "id": "test-prompt",
                            "major_version": "1",
                        },
                    ],
                },
            },
        }
        
        config_path = create_test_config(config_data)
        try:
            yaml_config = YamlConfig.model_validate(config_data)
            
            # Check V2 config is loaded
            v2_configs = yaml_config.get_v2_configs()
            assert len(v2_configs) == 1
            assert "autogenerate_v2" in v2_configs
            
            v2_config = v2_configs["autogenerate_v2"]
            assert v2_config.outfile == "v2_prompts.py"
            assert v2_config.app_id == "app_id_1"
            assert len(v2_config.prompts) == 1
        finally:
            os.remove(config_path)
    
    def test_multi_app_config(self):
        """Test the new multi-app V2 configuration."""
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
                                    "id": "search-prompt",
                                    "major_version": "1",
                                },
                                {
                                    "id": "summarize-prompt",
                                    "major_version": "2",
                                },
                            ],
                        },
                        {
                            "app_id": "app_id_2",
                            "outfile": "app2_prompts.py",
                            "prompts": [
                                {
                                    "id": "classify-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                        {
                            "app_id": "app_id_3",
                            "prompts": [
                                {
                                    "id": "chat-prompt",
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
            yaml_config = YamlConfig.model_validate(config_data)
            
            # Check V2 configs are loaded
            v2_configs = yaml_config.get_v2_configs()
            assert len(v2_configs) == 3
            
            # Check app 1
            app1_config = v2_configs["app_app_id_1"]
            assert app1_config.outfile == "app1_prompts.py"
            assert app1_config.app_id == "app_id_1"
            assert len(app1_config.prompts) == 2
            
            # Check app 2
            app2_config = v2_configs["app_app_id_2"]
            assert app2_config.outfile == "app2_prompts.py"
            assert app2_config.app_id == "app_id_2"
            assert len(app2_config.prompts) == 1
            
            # Check app 3 (uses default outfile)
            app3_config = v2_configs["app_app_id_3"]
            assert app3_config.outfile == "default_prompts.py"
            assert app3_config.app_id == "app_id_3"
            assert len(app3_config.prompts) == 1
        finally:
            os.remove(config_path)
    
    def test_mixed_config(self):
        """Test a configuration with both V1 and multiple V2 apps."""
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
                                    "id": "search-prompt",
                                    "major_version": "1",
                                },
                            ],
                        },
                        {
                            "app_id": "app_id_2",
                            "outfile": "app2_prompts.py",
                            "prompts": [
                                {
                                    "id": "classify-prompt",
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
            yaml_config = YamlConfig.model_validate(config_data)
            
            # Check V1 config is loaded
            assert yaml_config.autogenerate is not None
            assert yaml_config.autogenerate.prompts.outfile == "v1_prompts.py"
            assert len(yaml_config.autogenerate.prompts.prompts) == 1
            
            # Check V2 configs are loaded
            v2_configs = yaml_config.get_v2_configs()
            assert len(v2_configs) == 2
            assert "app_app_id_1" in v2_configs
            assert "app_app_id_2" in v2_configs
        finally:
            os.remove(config_path)
    
    def test_validation_missing_outfile(self):
        """Test validation when outfile is missing."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    # No default outfile
                    "apps": [
                        {
                            "app_id": "app_id_1",
                            # No app-specific outfile
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
            # Should fail validation
            with pytest.raises(ValueError, match="missing 'outfile'"):
                YamlConfig.model_validate(config_data)
        finally:
            os.remove(config_path)
    
    def test_validation_both_configs(self):
        """Test validation when both single and multi-app configs are specified."""
        config_data = {
            "autogenerate_v2": {
                "prompts": {
                    # Both single app and multi-app config
                    "outfile": "v2_prompts.py",
                    "app_id": "app_id_1",
                    "prompts": [
                        {
                            "id": "test-prompt",
                            "major_version": "1",
                        },
                    ],
                    "apps": [
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
        try:
            # Should fail validation
            with pytest.raises(ValueError, match="Cannot specify both 'prompts' and 'apps'"):
                YamlConfig.model_validate(config_data)
        finally:
            os.remove(config_path) 