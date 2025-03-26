from autoblocks._impl.prompts.v2.discovery.code_generator import CodeGenerator
from autoblocks._impl.prompts.v2.discovery.code_generator import parse_placeholders_from_template


class TestCodeGenerator:
    def test_generate_class_header_no_generics(self):
        # Test class header generation without generics
        result = CodeGenerator.generate_class_header("TestClass", "BaseClass")
        assert result == "class TestClass(BaseClass):\n"

    def test_generate_class_header_with_generics(self):
        # Test class header generation with generics
        result = CodeGenerator.generate_class_header("TestClass", "BaseClass", ["T1", "T2"])
        assert result == "class TestClass(BaseClass[T1, T2]):\n"

    def test_generate_class_attributes(self):
        # Test class attributes generation
        attributes = {
            "attr1": '"value1"',
            "attr2": "123",
            "attr3": "BaseClass",
        }
        result = CodeGenerator.generate_class_attributes(attributes)
        assert '    attr1 = "value1"\n' in result
        assert "    attr2 = 123\n" in result
        assert "    attr3 = BaseClass\n" in result

    def test_generate_dict_entries_empty(self):
        # Test empty dictionary generation
        result = CodeGenerator.generate_dict_entries({})
        assert result == "    __name_mapper__ = {}\n"

    def test_generate_dict_entries(self):
        # Test dictionary entries generation
        entries = {"key1": "value1", "key2": "value2"}
        result = CodeGenerator.generate_dict_entries(entries)
        assert '    __name_mapper__ = {\n        "key1": "value1",\n        "key2": "value2",\n    }\n' == result

    def test_generate_method(self):
        # Test method generation
        name = "test_method"
        params = ["param1: str", "param2: int"]
        body = ["line1", "line2", "return result"]
        return_type = "str"

        result = CodeGenerator.generate_method(name, params, body, False, return_type)

        assert "    def test_method(\n" in result
        assert "        self,\n" in result
        assert "        param1: str,\n" in result
        assert "        param2: int,\n" in result
        assert "    ) -> str:\n" in result
        assert "        line1\n" in result
        assert "        line2\n" in result
        assert "        return result\n" in result

    def test_generate_method_with_star_args(self):
        # Test method generation with star args
        name = "test_method"
        params = ["param1: str", "param2: int"]
        body = ["line1", "return result"]

        result = CodeGenerator.generate_method(name, params, body, True)

        assert "        *,\n" in result


class TestPlaceholderParsing:
    def test_parse_placeholders_from_template(self):
        # Test placeholder extraction
        template = "Hello {{name}}, welcome to {{place}}!"
        result = parse_placeholders_from_template(template)
        assert result == ["name", "place"]

    def test_parse_placeholders_with_whitespace(self):
        # Test placeholder extraction with whitespace
        template = "Hello {{ name }}, welcome to {{  place  }}!"
        result = parse_placeholders_from_template(template)
        assert result == ["name", "place"]

    def test_parse_placeholders_with_dash(self):
        # Test placeholder extraction with dashes
        template = "Value: {{customer-id}}"
        result = parse_placeholders_from_template(template)
        assert result == ["customer-id"]

    def test_parse_placeholders_empty(self):
        # Test empty template
        template = "No placeholders here!"
        result = parse_placeholders_from_template(template)
        assert result == []
