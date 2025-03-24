import logging
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import cast

from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.models import Prompt
from autoblocks._impl.prompts.v2.utils import indent
from autoblocks._impl.prompts.v2.utils import infer_type
from autoblocks._impl.prompts.v2.utils import normalize_app_name
from autoblocks._impl.prompts.v2.utils import to_snake_case
from autoblocks._impl.prompts.v2.utils import to_title_case

log = logging.getLogger(__name__)

# Type alias for app map structure
AppData = Dict[str, Any]


def generate_params_class_code(title_case_id: str, version: str, params: Dict[str, Any]) -> str:
    """
    Generate code for a params class.

    Args:
        title_case_id: The title-cased prompt ID
        version: The major version
        params: The parameters data

    Returns:
        The generated code
    """
    class_name = f"_{title_case_id}V{version}Params"

    auto = f"class {class_name}(FrozenModel):\n"
    if not params:
        auto += f"{indent()}pass\n"
        return auto

    # Extract params from the nested structure
    if isinstance(params, dict) and "params" in params:
        params = params["params"]

    for key, value in params.items():
        type_hint = infer_type(value)
        if type_hint is None:
            continue
        snake_case_key = to_snake_case(key)
        auto += f'{indent()}{snake_case_key}: {type_hint} = pydantic.Field(..., alias="{key}")\n'

    return auto


def parse_placeholders_from_template(template: str) -> List[str]:
    """
    Extract placeholders from a template.

    Args:
        template: The template string

    Returns:
        A list of placeholder names
    """
    import re

    # Match {{ placeholder }} pattern, capturing the name
    pattern = r"{{\s*([a-zA-Z0-9_-]+)\s*}}"
    matches = re.findall(pattern, template)
    return matches


def generate_template_renderer_class_code(title_case_id: str, version: str, templates: List[Dict[str, str]]) -> str:
    """
    Generate code for a template renderer class.

    Args:
        title_case_id: The title-cased prompt ID
        version: The major version
        templates: The templates data

    Returns:
        The generated code
    """
    class_name = f"_{title_case_id}V{version}TemplateRenderer"

    # Build a map of placeholder names
    placeholders = {}
    template_ids = []

    for template in templates:
        template_id = template["id"]
        template_ids.append(template_id)

        for placeholder in parse_placeholders_from_template(template["template"]):
            placeholders[placeholder] = to_snake_case(placeholder)

    # Generate the class code
    auto = f"class {class_name}(TemplateRenderer):\n"
    auto += f"{indent()}__name_mapper__ = {{\n"

    for name, snake_case in sorted(placeholders.items()):
        auto += f'{indent(2)}"{name}": "{snake_case}",\n'

    auto += f"{indent()}}}\n\n"

    # Add methods for each template
    for template_id in sorted(template_ids):
        snake_case_id = to_snake_case(template_id)
        template_data = next(t for t in templates if t["id"] == template_id)

        # Parse template placeholders
        template_placeholders = parse_placeholders_from_template(template_data["template"])

        # Generate method
        auto += f"{indent()}def {snake_case_id}(\n"
        auto += f"{indent(2)}self,\n"

        # Add parameters
        if template_placeholders:
            auto += f"{indent(2)}*,\n"

            # Skip duplicate placeholders
            seen_placeholders = set()
            for placeholder in template_placeholders:
                if placeholder in seen_placeholders:
                    continue
                seen_placeholders.add(placeholder)
                auto += f"{indent(2)}{to_snake_case(placeholder)}: str,\n"

        auto += f"{indent()}) -> str:\n"
        auto += f"{indent(2)}return self._render(\n"
        auto += f'{indent(3)}"{template_id}",\n'

        # Add parameters to _render call
        seen_placeholders = set()
        for placeholder in template_placeholders:
            if placeholder in seen_placeholders:
                continue
            seen_placeholders.add(placeholder)
            snake_case = to_snake_case(placeholder)
            auto += f"{indent(3)}{snake_case}={snake_case},\n"

        auto += f"{indent(2)})\n\n"

    return auto


def generate_tool_renderer_class_code(title_case_id: str, version: str, tools: List[Dict[str, Any]]) -> str:
    """
    Generate code for a tool renderer class.

    Args:
        title_case_id: The title-cased prompt ID
        version: The major version
        tools: The tools data

    Returns:
        The generated code
    """
    class_name = f"_{title_case_id}V{version}ToolRenderer"

    # Build a map of placeholder names
    placeholders = {}
    tool_names = []

    for tool in tools or []:
        name = tool["name"]
        tool_names.append(name)

        for param in tool.get("params", []):
            placeholders[param] = to_snake_case(param)

    # Generate the class code
    auto = f"class {class_name}(ToolRenderer):\n"
    auto += f"{indent()}__name_mapper__ = {{\n"

    for name, snake_case in sorted(placeholders.items()):
        auto += f'{indent(2)}"{name}": "{snake_case}",\n'

    auto += f"{indent()}}}\n\n"

    # Add methods for each tool
    for tool_name in sorted(tool_names):
        snake_case_name = to_snake_case(tool_name)
        tool_data = next(t for t in tools if t["name"] == tool_name)

        # Get tool parameters
        tool_params = tool_data.get("params", [])

        # Generate method
        auto += f"{indent()}def {snake_case_name}(\n"
        auto += f"{indent(2)}self,\n"

        # Add parameters
        if tool_params:
            auto += f"{indent(2)}*,\n"

            for param in tool_params:
                auto += f"{indent(2)}{to_snake_case(param)}: str,\n"

        auto += f"{indent()}) -> Dict[str, Any]:\n"
        auto += f"{indent(2)}return self._render(\n"
        auto += f'{indent(3)}"{tool_name}",\n'

        # Add parameters to _render call
        for param in tool_params:
            snake_case = to_snake_case(param)
            auto += f"{indent(3)}{snake_case}={snake_case},\n"

        auto += f"{indent(2)})\n\n"

    return auto


def generate_execution_context_class_code(title_case_id: str, version: str) -> str:
    """
    Generate code for an execution context class.

    Args:
        title_case_id: The title-cased prompt ID
        version: The major version

    Returns:
        The generated code
    """
    class_name = f"_{title_case_id}V{version}ExecutionContext"
    params_class = f"_{title_case_id}V{version}Params"
    template_renderer = f"_{title_case_id}V{version}TemplateRenderer"
    tool_renderer = f"_{title_case_id}V{version}ToolRenderer"

    auto = f"class {class_name}(\n"
    auto += f"{indent()}PromptExecutionContext[\n"
    auto += f"{indent(2)}{params_class},\n"
    auto += f"{indent(2)}{template_renderer},\n"
    auto += f"{indent(2)}{tool_renderer},\n"
    auto += f"{indent()}],\n"
    auto += "):\n"
    auto += f"{indent()}__params_class__ = {params_class}\n"
    auto += f"{indent()}__template_renderer_class__ = {template_renderer}\n"
    auto += f"{indent()}__tool_renderer_class__ = {tool_renderer}\n"

    return auto


def generate_manager_class_code(title_case_id: str, version: str, prompt_id: str, app_id: str) -> str:
    """
    Generate code for a prompt manager class.

    Args:
        title_case_id: The title-cased prompt ID
        version: The major version
        prompt_id: The original prompt ID
        app_id: The app ID

    Returns:
        The generated code
    """
    class_name = f"_{title_case_id}V{version}PromptManager"
    context_class = f"_{title_case_id}V{version}ExecutionContext"

    auto = f"class {class_name}(AutoblocksPromptManager[{context_class}]):\n"
    auto += f'{indent()}__app_id__ = "{app_id}"\n'
    auto += f'{indent()}__prompt_id__ = "{prompt_id}"\n'
    auto += f'{indent()}__prompt_major_version__ = "{version}"\n'
    auto += f"{indent()}__execution_context_class__ = {context_class}\n"

    return auto


def generate_factory_class_code(title_case_id: str, prompt_id: str, major_versions: List[str], app_id: str) -> str:
    """
    Generate code for a factory class.

    Args:
        title_case_id: The title-cased prompt ID
        prompt_id: The original prompt ID
        major_versions: The major versions
        app_id: The app ID

    Returns:
        The generated code
    """
    class_name = f"{title_case_id}Factory"

    auto = f"class {class_name}:\n"
    auto += f"{indent()}@staticmethod\n"
    auto += f"{indent()}def create(\n"
    auto += f"{indent(2)}major_version=None,\n"
    auto += f"{indent(2)}minor_version='0',\n"
    auto += f"{indent(2)}api_key=None,\n"
    auto += f"{indent(2)}init_timeout=None,\n"
    auto += f"{indent(2)}refresh_timeout=None,\n"
    auto += f"{indent(2)}refresh_interval=None,\n"
    auto += f"{indent(2)}):\n"

    # Default to latest version
    latest_version = max(major_versions)
    auto += f"{indent(2)}if major_version is None:\n"
    auto += f"{indent(3)}major_version = '{latest_version}'  # Latest version\n\n"

    # Add kwargs handling
    auto += f"{indent(2)}kwargs = {{}}\n"
    auto += f"{indent(2)}if api_key is not None:\n"
    auto += f"{indent(3)}kwargs['api_key'] = api_key\n"
    auto += f"{indent(2)}if init_timeout is not None:\n"
    auto += f"{indent(3)}kwargs['init_timeout'] = init_timeout\n"
    auto += f"{indent(2)}if refresh_timeout is not None:\n"
    auto += f"{indent(3)}kwargs['refresh_timeout'] = refresh_timeout\n"
    auto += f"{indent(2)}if refresh_interval is not None:\n"
    auto += f"{indent(3)}kwargs['refresh_interval'] = refresh_interval\n\n"

    # Factory logic
    for version in sorted(major_versions):
        auto += f"{indent(2)}if major_version == '{version}':\n"
        auto += f"{indent(3)}return _{title_case_id}V{version}PromptManager(minor_version=minor_version, **kwargs)\n"

    # Handle unknown versions
    available_versions = ", ".join(sorted(major_versions))
    error_msg = f"Unsupported major version: {{major_version}}. Available versions: {available_versions}"
    auto += f'{indent(2)}raise ValueError(f"{error_msg}")\n'

    return auto


def generate_prompt_implementations(app_id: str, app_name: str, prompt_data: Prompt) -> str:
    """
    Generate all implementations for a prompt.

    Args:
        app_id: The app ID
        app_name: The app name
        prompt_data: The prompt data

    Returns:
        The generated code
    """
    prompt_id = prompt_data.id
    title_case_id = to_title_case(prompt_id)

    # Extract all major versions
    major_versions = [mv.major_version for mv in prompt_data.major_versions]

    implementations = ["# Imports"]
    implementations.append("from typing import Any, Dict, List, Optional, Union")
    implementations.append("import pydantic")
    implementations.append("from autoblocks.prompts.v2.models import FrozenModel")
    implementations.append("from autoblocks.prompts.v2.context import PromptExecutionContext")
    implementations.append("from autoblocks.prompts.v2.manager import AutoblocksPromptManager")
    implementations.append("from autoblocks.prompts.v2.renderer import TemplateRenderer, ToolRenderer")
    implementations.append("")

    implementations.append(f"# Implementations for {prompt_id}")

    # Generate implementation for each major version
    for major_version in prompt_data.major_versions:
        version = major_version.major_version

        # Generate params class
        params_class = generate_params_class_code(
            title_case_id, version, major_version.params.dict() if major_version.params else {}
        )
        implementations.append(params_class)

        # Generate template renderer
        template_renderer = generate_template_renderer_class_code(
            title_case_id, version, [t.dict() for t in major_version.templates]
        )
        implementations.append(template_renderer)

        # Generate tool renderer
        tool_renderer = generate_tool_renderer_class_code(
            title_case_id, version, [t.dict() for t in major_version.tools_params] if major_version.tools_params else []
        )
        implementations.append(tool_renderer)

        # Generate execution context
        execution_context = generate_execution_context_class_code(title_case_id, version)
        implementations.append(execution_context)

        # Generate manager class
        manager_class = generate_manager_class_code(title_case_id, version, prompt_id, app_id)
        implementations.append(manager_class)

    # Generate factory class
    factory_class = generate_factory_class_code(title_case_id, prompt_id, major_versions, app_id)
    implementations.append(factory_class)

    return "\n\n".join(implementations)


def generate_app_init(app_name: str, app_id: str, prompts: List[Prompt], output_dir: str) -> None:
    """
    Generate the __init__.py file for an app.

    Args:
        app_name: The app name
        app_id: The app ID
        prompts: The prompts for this app
        output_dir: The output directory
    """
    normalized_name = normalize_app_name(app_name)
    app_dir = f"{output_dir}/apps/{normalized_name}"
    os.makedirs(app_dir, exist_ok=True)

    init_code = [
        "# Auto-generated prompt module for app: " + app_name,
        "from autoblocks._impl.prompts.v2.registry import PromptRegistry",
        "from . import prompts",
        "",
    ]

    # Export prompt factory functions
    for prompt in prompts:
        prompt_id = prompt.id
        snake_case = to_snake_case(prompt_id)
        function_name = f"{snake_case}_prompt_manager"

        init_code.append(f"def {function_name}(major_version=None, minor_version='0',")
        init_code.append("                  api_key=None, init_timeout=None,")
        init_code.append("                  refresh_timeout=None, refresh_interval=None):")
        init_code.append(f"    return prompts.{to_title_case(prompt_id)}Factory.create(")
        init_code.append("        major_version=major_version,")
        init_code.append("        minor_version=minor_version,")
        init_code.append("        api_key=api_key,")
        init_code.append("        init_timeout=init_timeout,")
        init_code.append("        refresh_timeout=refresh_timeout,")
        init_code.append("        refresh_interval=refresh_interval")
        init_code.append("    )")
        init_code.append("")

    # Write to file
    with open(f"{app_dir}/__init__.py", "w") as f:
        f.write("\n".join(init_code))

    # Register with registry
    init_code.append("# Register app with registry")
    init_code.append("app = PromptRegistry.register_app(")
    init_code.append(f"    app_id='{app_id}',")
    init_code.append(f"    app_name='{app_name}',")
    init_code.append(f"    normalized_name='{normalized_name}'")
    init_code.append(")")
    init_code.append("")

    # Register prompts with registry
    for prompt in prompts:
        prompt_id = prompt.id
        snake_case = to_snake_case(prompt_id)
        function_name = f"{snake_case}_prompt_manager"

        major_versions = [mv.major_version for mv in prompt.major_versions]
        major_versions_str = "[" + ", ".join(f"'{v}'" for v in major_versions) + "]"

        init_code.append("PromptRegistry.register_prompt(")
        init_code.append(f"    app_normalized_name='{normalized_name}',")
        init_code.append(f"    prompt_id='{prompt_id}',")
        init_code.append(f"    factory_func={function_name},")
        init_code.append(f"    major_versions={major_versions_str}")
        init_code.append(")")
        init_code.append("")


def generate_app_prompts(app_name: str, app_id: str, prompts: List[Prompt], output_dir: str) -> None:
    """
    Generate the prompts.py file for an app.

    Args:
        app_name: The app name
        app_id: The app ID
        prompts: The prompts for this app
        output_dir: The output directory
    """
    normalized_name = normalize_app_name(app_name)
    app_dir = f"{output_dir}/apps/{normalized_name}"
    os.makedirs(app_dir, exist_ok=True)

    # Generate implementations for each prompt
    prompt_impls = []
    for prompt in prompts:
        prompt_impls.append(generate_prompt_implementations(app_id, app_name, prompt))

    # Write to file
    with open(f"{app_dir}/prompts.py", "w") as f:
        f.write("\n\n".join(prompt_impls))


def create_root_init(apps: List[Dict[str, Any]], output_dir: str) -> None:
    """
    Create the root __init__.py file.

    Args:
        apps: The apps data
        output_dir: The output directory
    """
    # Create apps package __init__.py
    with open(f"{output_dir}/apps/__init__.py", "w") as f:
        f.write("# Auto-generated app package\n")

    # Create root __init__.py
    init_code = ["# Auto-generated prompt modules"]
    init_code.append("# DO NOT EDIT THIS FILE MANUALLY")
    init_code.append("\n# Import registry")
    init_code.append("from autoblocks._impl.prompts.v2.registry import PromptRegistry")
    init_code.append("")
    init_code.append("# Import all app modules")

    for app in apps:
        normalized_name = normalize_app_name(app["app_name"])
        init_code.append(f"from .apps import {normalized_name}")

    init_code.append("\n# Make apps available at top level")
    for app in apps:
        normalized_name = normalize_app_name(app["app_name"])
        init_code.append(f"{normalized_name} = {normalized_name}")

    # Write to file
    with open(f"{output_dir}/__init__.py", "w") as f:
        f.write("\n".join(init_code))


def generate_all_prompt_modules(api_key: Optional[str] = None, output_dir: Optional[str] = None) -> None:
    """
    Generate all prompt modules from the API.

    Args:
        api_key: The API key to use
        output_dir: The output directory
    """
    if not output_dir:
        raise ValueError("Output directory must be specified")

    log.info(f"Generating V2 prompt modules in {output_dir}")

    # Create client and fetch all prompts
    client = PromptsAPIClient(api_key=api_key)
    all_prompts = client.get_all_prompts()

    # Group prompts by app
    apps_map: Dict[str, AppData] = {}
    for prompt in all_prompts:
        app_id = prompt.app_id
        if app_id not in apps_map:
            apps_map[app_id] = {"app_id": app_id, "app_name": prompt.app_name, "prompts": []}
        # Ensure this is a List[Prompt] not Sequence[str]
        prompts_list = cast(List[Prompt], apps_map[app_id]["prompts"])
        prompts_list.append(prompt)

    # Create base directories only if we have apps to generate
    if apps_map:
        os.makedirs(f"{output_dir}/apps", exist_ok=True)

    # Generate code for each app
    for app_id, app_data in apps_map.items():
        app_name = app_data["app_name"]
        # Cast to ensure proper type recognition
        prompts = cast(List[Prompt], app_data["prompts"])

        # Generate app init
        generate_app_init(app_name, app_id, prompts, output_dir)

        # Generate app prompts
        generate_app_prompts(app_name, app_id, prompts, output_dir)

    # Create root init
    create_root_init(list(apps_map.values()), output_dir)

    log.info(f"Generated modules for {len(apps_map)} apps with {len(all_prompts)} prompts")
