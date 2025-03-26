import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.utils import indent
from autoblocks._impl.prompts.utils import infer_type
from autoblocks._impl.prompts.utils import to_snake_case
from autoblocks._impl.prompts.utils import to_title_case
from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.discovery.managers import generate_execution_context_class_code
from autoblocks._impl.prompts.v2.discovery.managers import generate_factory_class_code
from autoblocks._impl.prompts.v2.discovery.managers import generate_manager_class_code
from autoblocks._impl.prompts.v2.discovery.models import PromptData
from autoblocks._impl.prompts.v2.discovery.renderers import generate_template_renderer_class_code
from autoblocks._impl.prompts.v2.discovery.renderers import generate_tool_renderer_class_code
from autoblocks._impl.prompts.v2.models import Prompt

log = logging.getLogger(__name__)


def generate_params_class_code(title_case_id: str, version: str, params: Dict[str, Any]) -> str:
    """Generate code for a params class."""

    version_prefix = "Undeployed" if version == REVISION_UNDEPLOYED else f"V{version}"

    class_name = f"_{title_case_id}{version_prefix}Params"

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


def get_prompt_data(prompt: Prompt, api_client: Optional[PromptsAPIClient] = None) -> PromptData:
    """Get data for a prompt, handling both deployed and undeployed cases."""
    result = PromptData(
        id=prompt.id,
        app_id=prompt.app_id,
        app_name=prompt.app_name,
        is_undeployed=prompt.is_undeployed,
        major_versions=[],
        undeployed_data=None,
    )

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

        # Assign the populated list to the result
        result.major_versions = major_version_data
        return result

    # For undeployed prompts, fetch additional data if client provided
    if api_client:
        try:
            undeployed_data = api_client.get_undeployed_prompt(app_id=prompt.app_id, prompt_id=prompt.id)
            result.undeployed_data = {
                "params": undeployed_data.get("params", {}),
                "templates": undeployed_data.get("templates", []),
                "tools": undeployed_data.get("toolsParams", []),
            }
            log.info(f"Fetched undeployed revision for prompt {prompt.id}")
        except Exception as e:
            log.error(f"Failed to fetch undeployed revision for prompt {prompt.id}: {e}")

    return result


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
        title_case_id,
        version,
        prompt_id,
        app_id,
    )
    implementations.append(manager_class)

    return implementations


def generate_prompt_implementations(
    app_id: str, app_name: str, prompt_data: Prompt, api_client: Optional[PromptsAPIClient] = None
) -> str:
    """Generate all implementations for a prompt."""
    prompt_id = prompt_data.id
    title_case_id = to_title_case(prompt_id)

    implementations = []

    # Get necessary prompt data
    data = get_prompt_data(prompt_data, api_client)

    if data.is_undeployed:
        version_str = REVISION_UNDEPLOYED

        # Generate classes for the undeployed prompt if we have data
        if data.undeployed_data:
            undeployed_data = data.undeployed_data
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
        factory_class = generate_factory_class_code(title_case_id=title_case_id, major_versions=[], is_undeployed=True)
        implementations.append(factory_class)
    else:
        # Generate implementation for each major version
        major_versions = []
        for version_data in data.major_versions:
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
        factory_class = generate_factory_class_code(title_case_id=title_case_id, major_versions=major_versions)
        implementations.append(factory_class)

    return "\n\n".join(implementations)
