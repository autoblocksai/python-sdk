from typing import List

from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.utils import indent
from autoblocks._impl.prompts.v2.discovery.code_generator import CodeGenerator


def generate_execution_context_class_code(title_case_id: str, version: str) -> str:
    """Generate code for an execution context class.

    This class serves as a container for the params, template renderer, and tool renderer
    classes, and is used by the prompt manager to execute prompts.

    Args:
        title_case_id: The prompt ID in title case
        version: The version string for this prompt

    Returns:
        Generated code for the execution context class
    """
    # Determine class names based on version
    version_prefix = "Undeployed" if version == REVISION_UNDEPLOYED else f"V{version}"

    # Define class names for all components
    class_name = f"_{title_case_id}{version_prefix}ExecutionContext"
    params_class = f"_{title_case_id}{version_prefix}Params"
    template_renderer = f"_{title_case_id}{version_prefix}TemplateRenderer"
    tool_renderer = f"_{title_case_id}{version_prefix}ToolRenderer"

    # Generate the class header with generic parameters
    auto = CodeGenerator.generate_class_header(
        class_name, "PromptExecutionContext", [params_class, template_renderer, tool_renderer]
    )

    # Define class attributes
    attributes = {
        "__params_class__": params_class,
        "__template_renderer_class__": template_renderer,
        "__tool_renderer_class__": tool_renderer,
    }

    # Add attributes to the class
    auto += CodeGenerator.generate_class_attributes(attributes)

    return auto


def generate_manager_class_code(
    title_case_id: str,
    version: str,
    prompt_id: str,
    app_id: str,
) -> str:
    """Generate code for a prompt manager class.

    This class is the main entry point for working with a prompt. It handles communication
    with the Autoblocks API and provides methods for executing the prompt.

    Args:
        title_case_id: The prompt ID in title case
        version: The version string for this prompt
        prompt_id: The original prompt ID
        app_id: The ID of the app that contains this prompt

    Returns:
        Generated code for the prompt manager class
    """
    # Determine version prefix for class names
    version_prefix = "Undeployed" if version == REVISION_UNDEPLOYED else f"V{version}"

    # Define class name
    class_name = f"_{title_case_id}{version_prefix}PromptManager"

    execution_context_class = f"_{title_case_id}{version_prefix}ExecutionContext"

    # Generate the class header with execution context as generic parameter
    auto = CodeGenerator.generate_class_header(class_name, "AutoblocksPromptManager", [execution_context_class])

    # Define class attributes
    attributes = {
        "__app_id__": f'"{app_id}"',
        "__prompt_id__": f'"{prompt_id}"',
        "__prompt_major_version__": f'"{version}"',
        "__execution_context_class__": execution_context_class,
    }

    # Add attributes to class
    auto += CodeGenerator.generate_class_attributes(attributes)

    return auto


def generate_factory_class_code(
    title_case_id: str,
    major_versions: List[str],
    is_undeployed: bool = False,
) -> str:
    """Generate code for a factory class."""
    class_name = f"{title_case_id}Factory"

    # Prepare method signature and body
    params = [
        (
            'major_version: str = "' + REVISION_UNDEPLOYED + '"'
            if is_undeployed
            else "major_version: Optional[str] = None"
        ),
        'minor_version: str = "' + REVISION_LATEST + '"' if is_undeployed else 'minor_version: str = "0"',
        "api_key: Optional[str] = None",
        "init_timeout: Optional[float] = None",
        "refresh_timeout: Optional[float] = None",
        "refresh_interval: Optional[float] = None",
    ]

    # Determine return type
    if is_undeployed:
        return_type = f"_{title_case_id}UndeployedPromptManager"
    elif len(major_versions) == 1:
        return_type = f"_{title_case_id}V{major_versions[0]}PromptManager"
    else:
        return_type = f"Union[{', '.join([f'_{title_case_id}V{v}PromptManager' for v in sorted(major_versions)])}]"

    body_lines = [
        "kwargs: Dict[str, Any] = {}",
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
                f"return _{title_case_id}UndeployedPromptManager(minor_version=minor_version, **kwargs)",
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
        body_lines.append(f'raise ValueError("Unsupported major version. Available versions: {available_versions}")')

    # Generate the class
    auto = f"class {class_name}:\n"
    auto += f"{indent()}@staticmethod\n"
    auto += f"{indent()}def create(\n"

    # Add parameters with proper indentation
    for param in params:
        auto += f"{indent(2)}{param},\n"

    # Add return type
    auto += f"{indent(1)}) -> {return_type}:\n"

    # Add method body with proper indentation
    for line in body_lines:
        if line:
            auto += f"{indent(2)}{line}\n"
        else:
            auto += "\n"

    return auto
