from typing import Any
from typing import Callable
from typing import Dict
from typing import List

from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.utils import to_snake_case
from autoblocks._impl.prompts.v2.discovery.code_generator import CodeGenerator
from autoblocks._impl.prompts.v2.discovery.code_generator import parse_placeholders_from_template


def generate_code_for_renderer(
    title_case_id: str,
    version: str,
    items: List[Dict[str, Any]],
    base_class: str,
    id_key: str,
    content_key: str,
    method_return_type: str,
    extract_placeholders_fn: Callable[[Any], List[str]],
    is_tool: bool = False,
) -> str:
    """Generate code for a renderer class (template or tool)."""

    version_prefix = "Undeployed" if version == REVISION_UNDEPLOYED else f"V{version}"

    class_name = f"_{title_case_id}{version_prefix}{base_class}"

    # Build a map of placeholder names
    placeholders = {}
    item_ids = []

    for item in items:
        item_id = item[id_key]
        item_ids.append(item_id)

        for placeholder in extract_placeholders_fn(item[content_key] if not is_tool else item):
            placeholders[placeholder] = to_snake_case(placeholder)

    # Generate the class code
    auto = CodeGenerator.generate_class_header(class_name, base_class)
    auto += CodeGenerator.generate_dict_entries(placeholders)

    # Add methods for each item
    for item_id in sorted(item_ids):
        snake_case_id = to_snake_case(item_id)
        item_data = next(item for item in items if item[id_key] == item_id)

        # Get placeholders for this item
        if is_tool:
            item_placeholders = item_data.get("params", [])
        else:
            item_placeholders = extract_placeholders_fn(item_data[content_key])
            # Remove duplicates while preserving order
            seen = set()
            unique_placeholders = []
            for p in item_placeholders:
                if p not in seen:
                    seen.add(p)
                    unique_placeholders.append(p)
            item_placeholders = unique_placeholders

        # Prepare parameters and body for the method
        params = [f"{to_snake_case(p)}: str" for p in item_placeholders]
        body_lines = [
            "return self._render(",
            f'    "{item_id}",',
        ]

        for placeholder in item_placeholders:
            snake_case = to_snake_case(placeholder)
            body_lines.append(f"    {snake_case}={snake_case},")

        body_lines.append(")")

        # Generate the method
        auto += CodeGenerator.generate_method(
            snake_case_id, params, body_lines, star_args=bool(item_placeholders), return_type=method_return_type
        )

    return auto


def generate_template_renderer_class_code(title_case_id: str, version: str, templates: List[Dict[str, str]]) -> str:
    """Generate code for a template renderer class."""
    return generate_code_for_renderer(
        title_case_id,
        version,
        templates,
        "TemplateRenderer",
        "id",
        "template",
        "str",
        parse_placeholders_from_template,
    )


def generate_tool_renderer_class_code(title_case_id: str, version: str, tools: List[Dict[str, Any]]) -> str:
    """Generate code for a tool renderer class."""
    return generate_code_for_renderer(
        title_case_id,
        version,
        tools or [],
        "ToolRenderer",
        "name",
        "",
        "Dict[str, Any]",
        lambda tool: tool.get("params", []),
        is_tool=True,
    )
