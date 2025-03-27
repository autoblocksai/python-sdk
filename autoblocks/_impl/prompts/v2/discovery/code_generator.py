import re
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl.prompts.utils import indent


class CodeGenerator:
    """Helper class for generating code with consistent patterns."""

    @staticmethod
    def generate_class_header(class_name: str, base_class: str, generic_params: Optional[List[str]] = None) -> str:
        """Generate a class header with proper inheritance and generics."""
        if generic_params:
            generics = f"[{', '.join(generic_params)}]"
            return f"class {class_name}({base_class}{generics}):\n"
        return f"class {class_name}({base_class}):\n"

    @staticmethod
    def generate_class_attributes(attributes: Dict[str, str]) -> str:
        """Generate class attributes with proper indentation."""
        result = ""
        for name, value in attributes.items():
            if value.startswith('"') or value.startswith("'"):
                result += f"{indent()}{name} = {value}\n"
            else:
                result += f"{indent()}{name} = {value}\n"
        return result

    @staticmethod
    def generate_dict_entries(entries: Dict[str, str], level: int = 2) -> str:
        """Generate dictionary entries with proper indentation."""
        if not entries:
            return f"{indent()}__name_mapper__ = {{}}\n"

        result = f"{indent()}__name_mapper__ = {{\n"
        for key, value in sorted(entries.items()):
            result += f'{indent(level)}"{key}": "{value}",\n'
        result += f"{indent()}}}\n"
        return result

    @staticmethod
    def generate_method(
        name: str, params: List[str], body: List[str], star_args: bool = False, return_type: Optional[str] = None
    ) -> str:
        """Generate a method with params and body."""
        result = f"{indent()}def {name}(\n"
        result += f"{indent(2)}self,\n"

        if star_args and params:
            result += f"{indent(2)}*,\n"

        for param in params:
            result += f"{indent(2)}{param},\n"

        if return_type:
            result += f"{indent()}) -> {return_type}:\n"
        else:
            result += f"{indent()}):\n"

        for line in body:
            result += f"{indent(2)}{line}\n"

        return result

    @staticmethod
    def generate_function(name: str, params: Dict[str, str], body: List[str], return_type: Optional[str] = None) -> str:
        """Generate a function definition with parameters and docstring."""
        params_list = [f"{name}={default}" if default else name for name, default in params.items()]

        code = []
        code.append(f"def {name}({', '.join(params_list)})")
        if return_type:
            code[-1] += f" -> {return_type}"
        code[-1] += ":\n"

        for line in body:
            code.append(f"{indent()}{line}\n")

        return "".join(code)


def parse_placeholders_from_template(template: str) -> List[str]:
    """Extract placeholders from a template string."""
    pattern = r"{{\s*([a-zA-Z0-9_-]+)\s*}}"
    return re.findall(pattern, template)
