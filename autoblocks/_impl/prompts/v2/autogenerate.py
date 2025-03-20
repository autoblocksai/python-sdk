import re
from typing import Any, Dict, List, Optional

from autoblocks._impl.api.v2.client import AutoblocksAPIClient
from autoblocks._impl.api.v2.models import Prompt
from autoblocks._impl.prompts.autogenerate import (
    HEADER,
    indent,
    infer_type,
    to_snake_case,
    to_title_case,
)
from autoblocks._impl.prompts.v2.models import (
    AutogeneratePromptConfig,
    AutogeneratePromptsConfig,
)


def generate_params_class_code(title_case_id: str, params: Dict[str, Any]) -> str:
    """Generate code for a prompt parameters class."""
    auto = f"class {title_case_id}Params(FrozenModel):\n"
    if not params:
        auto += f"{indent()}pass\n"
        return auto

    for key, value in params.items():
        type_hint = infer_type(value)
        if type_hint is None:
            continue
        snake_case_key = to_snake_case(key)
        auto += f'{indent()}{snake_case_key}: {type_hint} = pydantic.Field(..., alias="{key}")\n'
    
    return auto


def generate_template_renderer_class_code(title_case_id: str, templates: List[Dict[str, str]]) -> str:
    """Generate code for a template renderer class."""
    from autoblocks._impl.prompts.placeholders import parse_placeholders_from_template
    
    # Build the name mapper dictionary
    placeholders = {}
    template_ids = []
    
    for template in templates:
        template_id = template["id"]
        template_ids.append(template_id)
        
        for placeholder in parse_placeholders_from_template(template["template"]):
            if not placeholder.is_escaped:
                placeholders[placeholder.name] = to_snake_case(placeholder.name)
                
    # Generate the class code
    auto = f"class {title_case_id}TemplateRenderer(TemplateRenderer):\n"
    auto += f"{indent()}__name_mapper__ = {{\n"
    
    for name, snake_case in sorted(placeholders.items()):
        auto += f'{indent(2)}"{name}": "{snake_case}",\n'
        
    auto += f"{indent()}}}\n\n"
    
    # Add methods for each template
    for template_id in sorted(template_ids):
        snake_case_id = to_snake_case(template_id)
        method_params = []
        
        template = next(t for t in templates if t["id"] == template_id)
        template_placeholders = [p for p in parse_placeholders_from_template(template["template"]) if not p.is_escaped]
        
        # Skip duplicate placeholders
        seen_placeholders = set()
        for placeholder in template_placeholders:
            if placeholder.name in seen_placeholders:
                continue
            seen_placeholders.add(placeholder.name)
            method_params.append(f"{to_snake_case(placeholder.name)}: str")
        
        # Generate method
        auto += f"{indent()}def {snake_case_id}(\n"
        auto += f"{indent(2)}self,\n"
        
        if method_params:
            auto += f"{indent(2)}*,\n"
            auto += ",\n".join(f"{indent(2)}{param}" for param in method_params)
            auto += ",\n"
            
        auto += f"{indent()}) -> str:\n"
        auto += f'{indent(2)}return self._render(\n'
        auto += f'{indent(3)}"{template_id}",\n'
        
        # Add parameters
        for placeholder in sorted(seen_placeholders):
            snake_case = to_snake_case(placeholder)
            auto += f'{indent(3)}{snake_case}={snake_case},\n'
            
        auto += f"{indent(2)})\n\n"
    
    return auto


def generate_tool_renderer_class_code(title_case_id: str, tools: List[Dict[str, Any]]) -> str:
    """Generate code for a tool renderer class."""
    auto = f"class {title_case_id}ToolRenderer(ToolRenderer):\n"
    
    if not tools:
        auto += f"{indent()}__name_mapper__ = {{}}\n"
        return auto
        
    # Implementation would be similar to template renderer but for tools
    # This is a simplified version
    auto += f"{indent()}__name_mapper__ = {{}}\n"
    
    return auto


def generate_execution_context_class_code(title_case_id: str) -> str:
    """Generate code for an execution context class."""
    auto = f"class {title_case_id}ExecutionContext(\n"
    auto += f"{indent()}PromptExecutionContext[\n"
    auto += f"{indent(2)}{title_case_id}Params,\n"
    auto += f"{indent(2)}{title_case_id}TemplateRenderer,\n"
    auto += f"{indent(2)}{title_case_id}ToolRenderer,\n"
    auto += f"{indent()}],\n"
    auto += f"):\n"
    auto += f"{indent()}__params_class__ = {title_case_id}Params\n"
    auto += f"{indent()}__template_renderer_class__ = {title_case_id}TemplateRenderer\n"
    auto += f"{indent()}__tool_renderer_class__ = {title_case_id}ToolRenderer\n"
    
    return auto


def generate_manager_class_code(
    title_case_id: str, 
    prompt_id: str, 
    major_version: str,
    app_id: str,
) -> str:
    """Generate code for a prompt manager class."""
    auto = f"class {title_case_id}PromptManager(\n"
    auto += f"{indent()}AutoblocksPromptManager[{title_case_id}ExecutionContext],\n"
    auto += f"):\n"
    auto += f'{indent()}__app_id__ = "{app_id}"\n'
    auto += f'{indent()}__prompt_id__ = "{prompt_id}"\n'
    auto += f'{indent()}__prompt_major_version__ = "{major_version}"\n'
    auto += f"{indent()}__execution_context_class__ = {title_case_id}ExecutionContext\n"
    
    return auto


def generate_code_for_prompt(
    app_id: str,
    prompt_id: str, 
    major_version: str,
    api_key: Optional[str] = None,
) -> str:
    """Generate code for a V2 prompt.
    
    Args:
        app_id: The app ID containing the prompt.
        prompt_id: The ID of the prompt to generate code for.
        major_version: The major version of the prompt.
        api_key: The API key to use. If None, will try to read from environment.
        
    Returns:
        The generated code.
    """
    client = AutoblocksAPIClient(api_key=api_key)
    
    # Use minor version "0" for generation
    prompt = client.get_prompt(
        app_id=app_id,
        prompt_id=prompt_id, 
        major_version=major_version, 
        minor_version="0"
    )
    
    # Extract the major version details
    major = None
    for mv in prompt.major_versions:
        if mv.major_version == major_version:
            major = mv
            break
            
    if not major:
        raise ValueError(f"Major version {major_version} not found for prompt {prompt_id}")
    
    # Convert the object structure to what the generation functions expect
    title_case_id = to_title_case(prompt_id)
    
    params_class_code = generate_params_class_code(
        title_case_id, major.params or {}
    )
    
    templates = [{"id": t.id, "template": t.template} for t in major.templates]
    template_renderer_code = generate_template_renderer_class_code(
        title_case_id, templates
    )
    
    tool_renderer_code = generate_tool_renderer_class_code(
        title_case_id, major.tools_params or []
    )
    
    execution_context_code = generate_execution_context_class_code(
        title_case_id
    )
    
    manager_code = generate_manager_class_code(
        title_case_id,
        prompt_id,
        major_version,
        app_id,
    )
    
    # Combine all the generated code
    return (
        HEADER +
        "\n\n" +
        params_class_code +
        "\n\n" +
        template_renderer_code +
        "\n\n" +
        tool_renderer_code +
        "\n\n" +
        execution_context_code +
        "\n\n" +
        manager_code
    )


def write_generated_code_for_config(
    config: AutogeneratePromptsConfig,
    api_key: Optional[str] = None,
) -> None:
    """Write generated code for a V2 prompt configuration.
    
    Args:
        config: The configuration to generate code for.
        api_key: The API key to use. If None, will try to read from environment.
    """
    app_id = config.app_id
    generated_codes = []
    
    for prompt_config in config.prompts:
        prompt_id = prompt_config.id
        major_version = prompt_config.major_version
        
        if major_version:
            code = generate_code_for_prompt(
                app_id=app_id,
                prompt_id=prompt_id,
                major_version=major_version,
                api_key=api_key,
            )
            generated_codes.append(code)
    
    # Join and write to file
    with open(config.outfile, "w") as f:
        f.write("\n\n".join(generated_codes)) 