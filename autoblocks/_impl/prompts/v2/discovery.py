import logging
import os
import re
import shutil
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import cast

from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
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


def parse_placeholders_from_template(template: str) -> List[str]:
    """Extract placeholders from a template string."""
    pattern = r"{{\s*([a-zA-Z0-9_-]+)\s*}}"
    return re.findall(pattern, template)


def generate_params_class_code(title_case_id: str, version: str, params: Dict[str, Any]) -> str:
    """Generate code for a params class."""
    # For undeployed versions, don't include the 'V' prefix
    if version == "Undeployed":
        class_name = f"_{title_case_id}{version}Params"
    else:
        class_name = f"_{title_case_id}V{version}Params"

    if not params:
        return f"class {class_name}(FrozenModel):\n{indent()}pass\n"

    # Extract params from the nested structure if needed
    if isinstance(params, dict) and "params" in params:
        params = params["params"]

    auto = f"class {class_name}(FrozenModel):\n"
    for key, value in params.items():
        type_hint = infer_type(value)
        if type_hint is None:
            continue
        snake_case_key = to_snake_case(key)
        auto += f'{indent()}{snake_case_key}: {type_hint} = pydantic.Field(..., alias="{key}")\n'

    return auto


def generate_code(
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
    # For undeployed versions, don't include the 'V' prefix
    if version == REVISION_UNDEPLOYED:
        class_name = f"_{title_case_id}{version}{base_class}"
    else:
        class_name = f"_{title_case_id}V{version}{base_class}"

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
    return generate_code(
        title_case_id, version, templates, "TemplateRenderer", "id", "template", "str", parse_placeholders_from_template
    )


def generate_tool_renderer_class_code(title_case_id: str, version: str, tools: List[Dict[str, Any]]) -> str:
    """Generate code for a tool renderer class."""
    return generate_code(
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


def generate_execution_context_class_code(title_case_id: str, version: str) -> str:
    """Generate code for an execution context class."""
    # For undeployed versions, don't include the 'V' prefix
    if version == REVISION_UNDEPLOYED:
        class_name = f"_{title_case_id}{version}ExecutionContext"
        params_class = f"_{title_case_id}{version}Params"
        template_renderer = f"_{title_case_id}{version}TemplateRenderer"
        tool_renderer = f"_{title_case_id}{version}ToolRenderer"
    else:
        class_name = f"_{title_case_id}V{version}ExecutionContext"
        params_class = f"_{title_case_id}V{version}Params"
        template_renderer = f"_{title_case_id}V{version}TemplateRenderer"
        tool_renderer = f"_{title_case_id}V{version}ToolRenderer"

    auto = CodeGenerator.generate_class_header(
        class_name, "PromptExecutionContext", [params_class, template_renderer, tool_renderer]
    )

    attributes = {
        "__params_class__": params_class,
        "__template_renderer_class__": template_renderer,
        "__tool_renderer_class__": tool_renderer,
    }

    auto += CodeGenerator.generate_class_attributes(attributes)
    return auto


def generate_manager_class_code(
    title_case_id: str,
    version: str,
    prompt_id: str,
    app_id: str,
    execution_context_class: Optional[str] = None,
) -> str:
    """Generate code for a prompt manager class."""
    # For undeployed versions, don't include the 'V' prefix
    if version == REVISION_UNDEPLOYED:
        class_name = f"_{title_case_id}UndeployedPromptManager"

        if execution_context_class is None:
            execution_context_class = f"_{title_case_id}UndeployedExecutionContext"
    else:
        class_name = f"_{title_case_id}V{version}PromptManager"

        if execution_context_class is None:
            execution_context_class = f"_{title_case_id}V{version}ExecutionContext"

    auto = CodeGenerator.generate_class_header(class_name, "AutoblocksPromptManager", [execution_context_class])

    attributes = {
        "__app_id__": f'"{app_id}"',
        "__prompt_id__": f'"{prompt_id}"',
        "__prompt_major_version__": f'"{version}"',
        "__execution_context_class__": execution_context_class,
    }

    auto += CodeGenerator.generate_class_attributes(attributes)
    return auto


def generate_factory_class_code(
    title_case_id: str,
    prompt_id: str,
    major_versions: List[str],
    app_id: str,
    is_undeployed: bool = False,
) -> str:
    """Generate code for a factory class."""
    class_name = f"{title_case_id}Factory"
    version_str = "Undeployed" if is_undeployed else None

    # Prepare method signature and body
    params = [
        'major_version="' + REVISION_UNDEPLOYED + '"' if is_undeployed else "major_version=None",
        'minor_version="' + REVISION_LATEST + '"' if is_undeployed else 'minor_version="0"',
        "api_key=None",
        "init_timeout=None",
        "refresh_timeout=None",
        "refresh_interval=None",
    ]

    body_lines = [
        "kwargs = {}",
        "if api_key is not None:",
        "    kwargs['api_key'] = api_key",
        "if init_timeout is not None:",
        "    kwargs['init_timeout'] = init_timeout",
        "if refresh_timeout is not None:",
        "    kwargs['refresh_timeout'] = refresh_timeout",
        "if refresh_interval is not None:",
        "    kwargs['refresh_interval'] = refresh_interval",
        "",
    ]

    # Add appropriate logic based on whether the prompt is deployed or not
    if is_undeployed:
        body_lines.extend(
            [
                "# Prompt has no deployed versions",
                f'if major_version != "{REVISION_UNDEPLOYED}":',
                '    raise ValueError("Unsupported major version. This prompt has no deployed versions.")',
                f"return _{title_case_id}{version_str}PromptManager(minor_version=minor_version, **kwargs)",
            ]
        )
    else:
        # Add default version selection
        if major_versions:
            latest_version = max(major_versions)
            body_lines.extend(
                [
                    "if major_version is None:",
                    f"    major_version = '{latest_version}'  # Latest version",
                    "",
                ]
            )

        # Add version-specific return statements
        for version in sorted(major_versions):
            body_lines.extend(
                [
                    f"if major_version == '{version}':",
                    f"    return _{title_case_id}V{version}PromptManager(minor_version=minor_version, **kwargs)",
                ]
            )

        # Add error handling for the last version
        available_versions = ", ".join(sorted(major_versions))
        body_lines.append("")  # Add blank line for readability
        body_lines.append(f'raise ValueError(f"Unsupported major version. Available versions: {available_versions}")')

    # Generate the class
    auto = f"class {class_name}:\n"
    auto += f"{indent()}@staticmethod\n"
    auto += f"{indent()}def create(\n"

    # Add self parameter and parameters with proper indentation
    auto += f"{indent(2)}self,\n"
    for param in params:
        auto += f"{indent(2)}{param},\n"
    auto += f"{indent(1)}):\n"

    # Add method body with proper indentation
    for line in body_lines:
        if line:
            auto += f"{indent(2)}{line}\n"
        else:
            auto += "\n"

    return auto


def generate_version_implementations(
    title_case_id: str,
    version: str,
    prompt_id: str,
    app_id: str,
    params: Dict[str, Any],
    templates: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> List[str]:
    """Generate implementations for a specific prompt version."""
    implementations = [
        generate_params_class_code(title_case_id, version, params),
        generate_template_renderer_class_code(title_case_id, version, templates),
        generate_tool_renderer_class_code(title_case_id, version, tools),
        generate_execution_context_class_code(title_case_id, version),
    ]

    # Generate manager class
    manager_class = generate_manager_class_code(
        title_case_id, version, prompt_id, app_id, execution_context_class=f"_{title_case_id}V{version}ExecutionContext"
    )
    implementations.append(manager_class)

    return implementations


def get_prompt_data(prompt: Prompt, api_client: Optional[PromptsAPIClient] = None) -> Dict[str, Any]:
    """Get data for a prompt, handling both deployed and undeployed cases."""
    result = {
        "id": prompt.id,
        "app_id": prompt.app_id,
        "app_name": prompt.app_name,
        "is_undeployed": prompt.is_undeployed,
        "major_versions": [],
        "undeployed_data": None,
    }

    # For deployed prompts, simply extract version data
    if not prompt.is_undeployed:
        major_version_data = []  # Create a new list to hold version data

        for major_version in prompt.major_versions:
            major_version_data.append(
                {
                    "version": major_version.major_version,
                    "params": major_version.params.dict() if major_version.params else {},
                    "templates": [t.dict() for t in major_version.templates],
                    "tools": [t.dict() for t in major_version.tools_params] if major_version.tools_params else [],
                }
            )

        # Assign the populated list to the result dictionary
        result["major_versions"] = major_version_data
        return result

    # For undeployed prompts, fetch additional data if client provided
    if api_client:
        try:
            undeployed_data = api_client.get_undeployed_prompt(app_id=prompt.app_id, prompt_id=prompt.id)
            result["undeployed_data"] = {
                "params": undeployed_data.get("params", {}),
                "templates": undeployed_data.get("templates", []),
                "tools": undeployed_data.get("toolsParams", []),
            }
            log.info(f"Fetched undeployed revision for prompt {prompt.id}")
        except Exception as e:
            log.error(f"Failed to fetch undeployed revision for prompt {prompt.id}: {e}")

    return result


def generate_prompt_implementations(
    app_id: str, app_name: str, prompt_data: Prompt, api_client: Optional[PromptsAPIClient] = None
) -> str:
    """Generate all implementations for a prompt."""
    prompt_id = prompt_data.id
    title_case_id = to_title_case(prompt_id)

    implementations = []

    # Get necessary prompt data
    data = get_prompt_data(prompt_data, api_client)

    if data["is_undeployed"]:
        version_str = "Undeployed"

        # Generate classes for the undeployed prompt if we have data
        if data["undeployed_data"]:
            undeployed_data = data["undeployed_data"]
            version_impls = generate_version_implementations(
                title_case_id,
                version_str,
                prompt_id,
                app_id,
                undeployed_data["params"],
                undeployed_data["templates"],
                undeployed_data["tools"],
            )

            implementations.extend(version_impls)
        else:
            # Generate a simple manager without execution context
            manager_class = generate_manager_class_code(title_case_id, version_str, prompt_id, app_id)
            implementations.append(manager_class)

        # Generate factory class for undeployed prompt
        factory_class = generate_factory_class_code(
            title_case_id=title_case_id, prompt_id=prompt_id, major_versions=[], app_id=app_id, is_undeployed=True
        )
        implementations.append(factory_class)
    else:
        # Generate implementation for each major version
        major_versions = []
        for version_data in data["major_versions"]:
            version = version_data["version"]
            major_versions.append(version)

            # Generate all implementations for this version
            version_impls = generate_version_implementations(
                title_case_id,
                version,
                prompt_id,
                app_id,
                version_data["params"],
                version_data["templates"],
                version_data["tools"],
            )
            implementations.extend(version_impls)

        # Generate factory class for deployed prompts
        factory_class = generate_factory_class_code(
            title_case_id=title_case_id, prompt_id=prompt_id, major_versions=major_versions, app_id=app_id
        )
        implementations.append(factory_class)

    return "\n\n".join(implementations)


def ensure_directory_exists(directory_path: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory_path, exist_ok=True)


def clean_output_directory(output_dir: str) -> None:
    """Clean up an existing output directory to prepare for generation."""
    if not os.path.exists(output_dir):
        return

    log.info(f"Cleaning up existing directory: {output_dir}")

    # Log which files we're about to delete
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            path = os.path.join(root, file)
            log.debug(f"Removing file: {path}")

    # Only remove files in the apps directory and the __init__.py file
    apps_dir = os.path.join(output_dir, "apps")
    if os.path.exists(apps_dir):
        shutil.rmtree(apps_dir)

    init_file = os.path.join(output_dir, "__init__.py")
    if os.path.exists(init_file):
        os.remove(init_file)


def generate_function_code(function_name: str, params: Dict[str, str], body: List[str]) -> str:
    """Generate a function definition with parameters and docstring."""
    params_list = [f"{name}={default}" if default else name for name, default in params.items()]

    code = []
    code.append(f"def {function_name}({', '.join(params_list)}):\n")
    for line in body:
        code.append(f"{indent()}{line}\n")

    return "".join(code)


def generate_app_init(app_name: str, app_id: str, prompts: List[Prompt], output_dir: str) -> None:
    """Generate the __init__.py file for an app."""
    normalized_name = normalize_app_name(app_name)
    app_dir = f"{output_dir}/apps/{normalized_name}"
    ensure_directory_exists(app_dir)

    init_code = [
        "# Auto-generated prompt module for app: " + app_name,
        "from . import prompts",
        "",
    ]

    # Export prompt factory functions
    for prompt in prompts:
        prompt_id = prompt.id
        title_case_id = to_title_case(prompt_id)
        snake_case = to_snake_case(prompt_id)
        function_name = f"{snake_case}_prompt_manager"

        # Function parameters with defaults
        init_code.extend(
            [
                f"def {function_name}(major_version=None, minor_version='0',",
                "                  api_key=None, init_timeout=None,",
                "                  refresh_timeout=None, refresh_interval=None):",
                f"    return prompts.{title_case_id}Factory.create(",
                "        major_version=major_version,",
                "        minor_version=minor_version,",
                "        api_key=api_key,",
                "        init_timeout=init_timeout,",
                "        refresh_timeout=refresh_timeout,",
                "        refresh_interval=refresh_interval",
                "    )",
                "",
            ]
        )

    # Write to file
    with open(f"{app_dir}/__init__.py", "w") as f:
        f.write("\n".join(init_code))


def create_root_init(apps: List[Dict[str, Any]], output_dir: str) -> None:
    """Create the root __init__.py file."""
    # Create apps package __init__.py
    apps_dir = f"{output_dir}/apps"
    ensure_directory_exists(apps_dir)

    with open(f"{apps_dir}/__init__.py", "w") as f:
        f.write("# Auto-generated app package\n")

    # Create root __init__.py with imports
    init_lines = ["# Auto-generated prompt modules", "# DO NOT EDIT THIS FILE MANUALLY", "", "# Import all app modules"]

    # Add import statements for apps
    app_names = [normalize_app_name(app["app_name"]) for app in apps]
    init_lines.extend([f"from .apps import {name}" for name in app_names])

    # Add module-level variables
    init_lines.append("\n# Make apps available at top level")
    init_lines.extend([f"{name} = {name}" for name in app_names])

    # Write to file
    with open(f"{output_dir}/__init__.py", "w") as f:
        f.write("\n".join(init_lines))


def generate_app_prompts(
    app_name: str, app_id: str, prompts: List[Prompt], output_dir: str, api_client: Optional[PromptsAPIClient] = None
) -> None:
    """Generate the prompts.py file for an app."""
    normalized_name = normalize_app_name(app_name)
    app_dir = f"{output_dir}/apps/{normalized_name}"
    ensure_directory_exists(app_dir)

    # Add imports at the beginning of the file
    imports = [
        "from typing import Any",
        "from typing import Dict",
        "from typing import List",
        "from typing import Optional",
        "from typing import Union",
        "",
        "import pydantic",
        "",
        "from autoblocks.prompts.v2.models import FrozenModel",
        "from autoblocks.prompts.v2.context import PromptExecutionContext",
        "from autoblocks.prompts.v2.manager import AutoblocksPromptManager",
        "from autoblocks.prompts.v2.renderer import TemplateRenderer, ToolRenderer",
        "",
        "",
    ]

    # Generate implementations for each prompt, removing any existing imports
    prompt_impls = []
    for prompt in prompts:
        implementation = generate_prompt_implementations(app_id, app_name, prompt, api_client)

        # No need to check for imports since we've removed them in generate_prompt_implementations
        prompt_impls.append(implementation)

    # Write to file with two empty lines between classes
    with open(f"{app_dir}/prompts.py", "w") as f:
        f.write("\n".join(imports) + "\n" + "\n".join(prompt_impls))


def generate_all_prompt_modules(api_key: Optional[str] = None, output_dir: Optional[str] = None) -> None:
    """Generate all prompt modules from the API."""
    if not output_dir:
        raise ValueError("Output directory must be specified")

    log.info(f"Generating V2 prompt modules in {output_dir}")

    # Clean up existing directory if it exists
    clean_output_directory(output_dir)

    # Create client and fetch all prompts
    client = PromptsAPIClient(api_key=api_key)
    all_prompts = client.get_all_prompts()

    # Group prompts by app
    apps_map: Dict[str, AppData] = {}
    for prompt in all_prompts:
        app_id = prompt.app_id
        if app_id not in apps_map:
            apps_map[app_id] = {"app_id": app_id, "app_name": prompt.app_name, "prompts": []}
        prompts_list = cast(List[Prompt], apps_map[app_id]["prompts"])
        prompts_list.append(prompt)

    # Create base directories
    ensure_directory_exists(output_dir)
    if apps_map:
        ensure_directory_exists(f"{output_dir}/apps")

    # Generate code for each app
    for app_id, app_data in apps_map.items():
        app_name = app_data["app_name"]
        prompts = cast(List[Prompt], app_data["prompts"])

        # Generate app files
        generate_app_init(app_name, app_id, prompts, output_dir)
        generate_app_prompts(app_name, app_id, prompts, output_dir, client)

    # Create root init
    create_root_init(list(apps_map.values()), output_dir)

    log.info(f"Generated modules for {len(apps_map)} apps with {len(all_prompts)} prompts")
