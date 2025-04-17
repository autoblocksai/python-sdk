from unittest.mock import patch

from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.v2.discovery.renderers import generate_code_for_renderer
from autoblocks._impl.prompts.v2.discovery.renderers import generate_template_renderer_class_code
from autoblocks._impl.prompts.v2.discovery.renderers import generate_tool_renderer_class_code


class TestRenderers:
    def test_generate_code_for_renderer_templates(self):
        # Test code generation for a template renderer
        title_case_id = "TestPrompt"
        version = "1"
        templates = [
            {"id": "template1", "template": "Hello {{name}}!"},
            {"id": "template2", "template": "Welcome to {{place}}!"},
        ]

        result = generate_code_for_renderer(
            title_case_id=title_case_id,
            version=version,
            items=templates,
            base_class="TemplateRenderer",
            id_key="id",
            content_key="template",
            method_return_type="str",
            extract_placeholders_fn=lambda t: ["name"] if "name" in t else ["place"],
        )

        # Check class definition
        assert "_TestPromptV1TemplateRenderer" in result
        assert "class _TestPromptV1TemplateRenderer(TemplateRenderer):" in result

        # Check name mapper
        assert "__name_mapper__ = {" in result
        assert '"name": "name"' in result
        assert '"place": "place"' in result

        # Check template methods
        assert "def template1(" in result
        assert "def template2(" in result
        assert "name: str" in result
        assert "place: str" in result
        assert "return self._render(" in result
        assert '"template1"' in result
        assert '"template2"' in result

    def test_generate_code_for_renderer_tools(self):
        # Test code generation for a tool renderer
        title_case_id = "TestPrompt"
        version = REVISION_UNDEPLOYED
        tools = [
            {"name": "tool1", "params": ["param1", "param2"]},
            {"name": "tool2", "params": ["param3"]},
        ]

        result = generate_code_for_renderer(
            title_case_id=title_case_id,
            version=version,
            items=tools,
            base_class="ToolRenderer",
            id_key="name",
            content_key="",
            method_return_type="Dict[str, Any]",
            extract_placeholders_fn=lambda t: t.get("params", []),
            is_tool=True,
        )

        # Check class definition
        assert "_TestPromptUndeployedToolRenderer" in result
        assert "class _TestPromptUndeployedToolRenderer(ToolRenderer):" in result

        # Check name mapper
        assert "__name_mapper__ = {" in result
        assert '"param1": "param1"' in result
        assert '"param2": "param2"' in result
        assert '"param3": "param3"' in result

        # Check tool methods
        assert "def tool1(" in result
        assert "def tool2(" in result
        assert "param1: str" in result
        assert "param2: str" in result
        assert "param3: str" in result
        assert "return self._render(" in result
        assert '"tool1"' in result
        assert '"tool2"' in result

    def test_generate_template_renderer_class_code(self):
        # Test the template renderer code generation wrapper
        with patch("autoblocks._impl.prompts.v2.discovery.renderers.generate_code_for_renderer") as mock_generate:
            mock_generate.return_value = "mocked renderer code"

            templates = [{"id": "template1", "template": "Test"}]
            title_case_id = "TestPrompt"
            version = "1"

            result = generate_template_renderer_class_code(
                title_case_id=title_case_id, version=version, templates=templates
            )

            # Verify correct parameters were passed
            mock_generate.assert_called_once()

            # Check the arguments without relying on keyword arguments
            args, kwargs = mock_generate.call_args
            assert len(args) >= 1 and args[0] == "TestPrompt"  # title_case_id as first positional arg
            assert len(args) >= 2 and args[1] == "1"  # version as second positional arg
            assert len(args) >= 3 and args[2] == templates  # templates as third positional arg
            assert kwargs.get("base_class", args[3] if len(args) > 3 else None) == "TemplateRenderer"
            assert kwargs.get("id_key", args[4] if len(args) > 4 else None) == "id"
            assert kwargs.get("content_key", args[5] if len(args) > 5 else None) == "template"
            assert kwargs.get("method_return_type", args[6] if len(args) > 6 else None) == "str"

            # Verify the result
            assert result == "mocked renderer code"

    def test_generate_tool_renderer_class_code(self):
        # Test the tool renderer code generation wrapper
        with patch("autoblocks._impl.prompts.v2.discovery.renderers.generate_code_for_renderer") as mock_generate:
            mock_generate.return_value = "mocked tool renderer code"

            tools = [{"name": "tool1", "params": ["param1"]}]
            title_case_id = "TestPrompt"
            version = "1"

            result = generate_tool_renderer_class_code(title_case_id=title_case_id, version=version, tools=tools)

            # Verify correct parameters were passed
            mock_generate.assert_called_once()

            # Check the arguments without relying on keyword arguments
            args, kwargs = mock_generate.call_args
            assert len(args) >= 1 and args[0] == "TestPrompt"  # title_case_id as first positional arg
            assert len(args) >= 2 and args[1] == "1"  # version as second positional arg
            assert len(args) >= 3 and args[2] == tools  # tools as third positional arg
            assert kwargs.get("base_class", args[3] if len(args) > 3 else None) == "ToolRenderer"
            assert kwargs.get("id_key", args[4] if len(args) > 4 else None) == "name"
            assert kwargs.get("content_key", args[5] if len(args) > 5 else None) == ""
            assert kwargs.get("method_return_type", args[6] if len(args) > 6 else None) == "Dict[str, Any]"
            assert kwargs.get("is_tool", False) is True

            # Verify the result
            assert result == "mocked tool renderer code"
