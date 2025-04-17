from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.v2.discovery.managers import generate_execution_context_class_code
from autoblocks._impl.prompts.v2.discovery.managers import generate_factory_class_code
from autoblocks._impl.prompts.v2.discovery.managers import generate_manager_class_code


class TestManagers:
    def test_generate_execution_context_class_code(self):
        # Test execution context class generation
        title_case_id = "TestPrompt"
        version = "1"

        result = generate_execution_context_class_code(title_case_id, version)

        # Check class definition
        assert "class _TestPromptV1ExecutionContext(PromptExecutionContext" in result

        # Check class attributes
        assert "__params_class__ = _TestPromptV1Params" in result
        assert "__template_renderer_class__ = _TestPromptV1TemplateRenderer" in result
        assert "__tool_renderer_class__ = _TestPromptV1ToolRenderer" in result

    def test_generate_execution_context_class_code_undeployed(self):
        # Test execution context class generation for undeployed prompts
        title_case_id = "TestPrompt"
        version = REVISION_UNDEPLOYED

        result = generate_execution_context_class_code(title_case_id, version)

        # Check class definition with "Undeployed" prefix
        assert "class _TestPromptUndeployedExecutionContext(PromptExecutionContext" in result

        # Check class attributes
        assert "__params_class__ = _TestPromptUndeployedParams" in result
        assert "__template_renderer_class__ = _TestPromptUndeployedTemplateRenderer" in result
        assert "__tool_renderer_class__ = _TestPromptUndeployedToolRenderer" in result

    def test_generate_manager_class_code(self):
        # Test manager class generation
        title_case_id = "TestPrompt"
        version = "1"
        prompt_id = "test-prompt"
        app_id = "test-app"

        result = generate_manager_class_code(title_case_id, version, prompt_id, app_id)

        # Check class definition
        assert "class _TestPromptV1PromptManager(AutoblocksPromptManager" in result

        # Check class attributes
        assert '__app_id__ = "test-app"' in result
        assert '__prompt_id__ = "test-prompt"' in result
        assert '__prompt_major_version__ = "1"' in result
        assert "__execution_context_class__ = _TestPromptV1ExecutionContext" in result

    def test_generate_factory_class_code_with_versions(self):
        # Test factory class generation with multiple versions
        title_case_id = "TestPrompt"
        major_versions = ["1", "2", "3"]

        result = generate_factory_class_code(title_case_id, major_versions)

        # Check class definition
        assert "class TestPromptFactory:" in result
        assert "@staticmethod" in result
        assert "def create(" in result

        # Check return type
        assert "-> Union[_TestPromptV1PromptManager, _TestPromptV2PromptManager, _TestPromptV3PromptManager]:" in result

        # Check version handling
        assert "if major_version is None:" in result
        assert "major_version = '3'  # Latest version" in result
        assert "if major_version == '1':" in result
        assert "return _TestPromptV1PromptManager(minor_version=minor_version, **kwargs)" in result
        assert "if major_version == '2':" in result
        assert "return _TestPromptV2PromptManager(minor_version=minor_version, **kwargs)" in result
        assert "if major_version == '3':" in result
        assert "return _TestPromptV3PromptManager(minor_version=minor_version, **kwargs)" in result

        # Check error handling
        assert 'raise ValueError("Unsupported major version. Available versions: 1, 2, 3")' in result

    def test_generate_factory_class_code_single_version(self):
        # Test factory class generation with a single version
        title_case_id = "TestPrompt"
        major_versions = ["1"]

        result = generate_factory_class_code(title_case_id, major_versions)

        # Check return type
        assert "-> _TestPromptV1PromptManager:" in result

        # Check version handling
        assert "if major_version is None:" in result
        assert "major_version = '1'  # Latest version" in result
        assert "if major_version == '1':" in result
        assert "return _TestPromptV1PromptManager(minor_version=minor_version, **kwargs)" in result

    def test_generate_factory_class_code_undeployed(self):
        # Test factory class generation for undeployed prompts
        title_case_id = "TestPrompt"
        major_versions: list[str] = []

        result = generate_factory_class_code(title_case_id, major_versions, is_undeployed=True)

        # Check return type
        assert "-> _TestPromptUndeployedPromptManager:" in result

        # Check version handling for undeployed
        assert 'major_version: str = "undeployed"' in result
        assert 'if major_version != "undeployed":' in result
        assert 'raise ValueError("Unsupported major version. This prompt has no deployed versions.")' in result
        assert "return _TestPromptUndeployedPromptManager(minor_version=minor_version, **kwargs)" in result
