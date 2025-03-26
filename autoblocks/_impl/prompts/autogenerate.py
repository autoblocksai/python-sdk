from typing import Any
from typing import Dict
from typing import List

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.models import AutogeneratePromptsConfig
from autoblocks._impl.prompts.models import FrozenModel
from autoblocks._impl.prompts.placeholders import TemplatePlaceholder
from autoblocks._impl.prompts.placeholders import parse_placeholders_from_template
from autoblocks._impl.prompts.utils import indent
from autoblocks._impl.prompts.utils import infer_type
from autoblocks._impl.prompts.utils import to_snake_case
from autoblocks._impl.prompts.utils import to_title_case
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component


class Template(FrozenModel):
    id: str
    placeholders: List[TemplatePlaceholder]

    @property
    def snake_case_id(self) -> str:
        return to_snake_case(self.id)


class Tool(FrozenModel):
    name: str
    placeholders: List[str]

    @property
    def snake_case_name(self) -> str:
        return to_snake_case(self.name)


class PromptCodegen(FrozenModel):
    id: str
    major_version: str
    params: Dict[str, Any]
    templates: List[Template]
    tools: List[Tool]

    @property
    def title_case_id(self) -> str:
        return to_title_case(self.id)

    @property
    def params_class_name(self) -> str:
        return f"{self.title_case_id}Params"

    @property
    def template_renderer_class_name(self) -> str:
        return f"{self.title_case_id}TemplateRenderer"

    @property
    def tool_renderer_class_name(self) -> str:
        return f"{self.title_case_id}ToolRenderer"

    @property
    def execution_context_class_name(self) -> str:
        return f"{self.title_case_id}ExecutionContext"

    @property
    def manager_class_name(self) -> str:
        return f"{self.title_case_id}PromptManager"


HEADER = """############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from typing import Any  # noqa: F401
from typing import Dict  # noqa: F401
from typing import Union  # noqa: F401

import pydantic  # noqa: F401

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer
from autoblocks.prompts.renderer import ToolRenderer

"""


def generate_params_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.params_class_name}(FrozenModel):\n"
    if not prompt.params:
        auto += f"{indent()}pass\n"
        return auto

    for key, value in prompt.params.items():
        type_hint = infer_type(value)
        if type_hint is None:
            continue
        snake_case_key = to_snake_case(key)
        auto += f'{indent()}{snake_case_key}: {type_hint} = pydantic.Field(..., alias="{key}")\n'

    return auto


def generate_template_render_method_code(template: Template) -> str:
    auto = f"{indent()}def {template.snake_case_id}(\n{indent(2)}self,\n"

    if template.placeholders:
        # Require all params to be passed in as keyword arguments
        auto += f"{indent(2)}*,\n"

    for placeholder in template.placeholders:
        auto += f"{indent(2)}{to_snake_case(placeholder.name)}: str,\n"

    auto += f"{indent()}) -> str:\n"
    auto += f'{indent(2)}return self._render(\n{indent(3)}"{template.id}",\n'

    for placeholder in template.placeholders:
        kwarg_name = to_snake_case(placeholder.name)
        auto += f"{indent(3)}{kwarg_name}={kwarg_name},\n"

    auto += f"{indent(2)})\n"

    return auto


def generate_template_renderer_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.template_renderer_class_name}(TemplateRenderer):\n"

    # Add name mapper class attribute
    # The name mapper maps the original template placeholder name
    # to the snake case name of the corresponding keyword argument
    name_mapper = {}
    for template in prompt.templates:
        for placeholder in template.placeholders:
            # We should have filtered out escaped placeholders earlier
            assert not placeholder.is_escaped
            name_mapper[placeholder.name] = to_snake_case(placeholder.name)

    if name_mapper:
        auto += f"{indent()}__name_mapper__ = {{\n"

        for key in sorted(name_mapper.keys()):
            auto += f'{indent(2)}"{key}": "{name_mapper[key]}",\n'

        auto += f"{indent()}}}\n\n"
    else:
        auto += f"{indent()}__name_mapper__ = {{}}\n\n"

    auto += "\n".join(generate_template_render_method_code(template) for template in prompt.templates)

    return auto


def generate_tool_render_method_code(tool: Tool) -> str:
    auto = f"{indent()}def {tool.snake_case_name}(\n{indent(2)}self,\n"

    if tool.placeholders:
        # Require all params to be passed in as keyword arguments
        auto += f"{indent(2)}*,\n"

    for placeholder in tool.placeholders:
        auto += f"{indent(2)}{to_snake_case(placeholder)}: str,\n"

    auto += f"{indent()}) -> Dict[str, Any]:\n"
    auto += f'{indent(2)}return self._render(\n{indent(3)}"{tool.name}",\n'

    for placeholder in tool.placeholders:
        kwarg_name = to_snake_case(placeholder)
        auto += f"{indent(3)}{kwarg_name}={kwarg_name},\n"

    auto += f"{indent(2)})\n"

    return auto


def generate_tool_renderer_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.tool_renderer_class_name}(ToolRenderer):\n"

    # Add name mapper class attribute
    # The name mapper maps the original tool placeholder name
    # to the snake case name of the corresponding keyword argument
    name_mapper = {}
    for tool in prompt.tools:
        for placeholder in tool.placeholders:
            name_mapper[placeholder] = to_snake_case(placeholder)

    if name_mapper:
        auto += f"{indent()}__name_mapper__ = {{\n"

        for key in sorted(name_mapper.keys()):
            auto += f'{indent(2)}"{key}": "{name_mapper[key]}",\n'

        auto += f"{indent()}}}\n\n"
    else:
        auto += f"{indent()}__name_mapper__ = {{}}\n\n"

    auto += "\n".join(generate_tool_render_method_code(tool) for tool in prompt.tools)

    return auto


def generate_execution_context_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.execution_context_class_name}(\n"
    auto += f"{indent()}PromptExecutionContext[\n"
    auto += f"{indent(2)}{prompt.params_class_name},\n"
    auto += f"{indent(2)}{prompt.template_renderer_class_name},\n"
    auto += f"{indent(2)}{prompt.tool_renderer_class_name},\n"
    auto += f"{indent()}],\n"
    auto += "):\n"
    auto += f"{indent()}__params_class__ = {prompt.params_class_name}\n"
    auto += f"{indent()}__template_renderer_class__ = {prompt.template_renderer_class_name}\n"
    auto += f"{indent()}__tool_renderer_class__ = {prompt.tool_renderer_class_name}\n"

    return auto


def generate_prompt_manager_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.manager_class_name}(\n"
    auto += f"{indent()}AutoblocksPromptManager[{prompt.execution_context_class_name}],\n"
    auto += "):\n"
    auto += f'{indent()}__prompt_id__ = "{prompt.id}"\n'
    auto += f'{indent()}__prompt_major_version__ = "{prompt.major_version}"\n'
    auto += f"{indent()}__execution_context_class__ = {prompt.execution_context_class_name}\n"
    return auto + "\n"


def generate_code_for_prompt(prompt: PromptCodegen) -> str:
    return "\n\n".join(
        [
            x
            for x in [
                generate_params_class_code(prompt),
                generate_template_renderer_class_code(prompt),
                generate_tool_renderer_class_code(prompt),
                generate_execution_context_class_code(prompt),
                generate_prompt_manager_class_code(prompt),
            ]
            if x is not None
        ],
    )


def make_prompts_from_config(
    config: AutogeneratePromptsConfig,
) -> List[PromptCodegen]:
    """
    Fetches prompt data from the Autoblocks API and generates code for each prompt
    configured in the .autoblocks.yml config file.
    """
    prompts = []

    for prompt in config.prompts:
        if prompt.major_version is not None:
            major = prompt.major_version
            minor = REVISION_LATEST
        elif prompt.dangerously_use_undeployed_revision is not None:
            major = REVISION_UNDEPLOYED
            minor = prompt.dangerously_use_undeployed_revision
        else:
            raise ValueError(
                f"Error in {prompt.id} config: "
                f"Either `major_version` or `dangerously_use_undeployed_revision` must be specified"
            )
        prompt_id = encode_uri_component(prompt.id)
        major_version = encode_uri_component(major)
        minor_version = encode_uri_component(minor)
        resp = httpx.get(
            url=f"{API_ENDPOINT}/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}",
            headers={"Authorization": f"Bearer {AutoblocksEnvVar.API_KEY.get()}"},
        )
        resp.raise_for_status()
        data = resp.json()

        try:
            params = data["params"]["params"] or {}
        except (KeyError, TypeError):
            params = {}

        templates = []
        for template in data["templates"]:
            template_id = template["id"]
            template_placeholders = parse_placeholders_from_template(template["template"])
            templates.append(
                Template(
                    id=template_id,
                    placeholders=[p for p in template_placeholders if not p.is_escaped],
                ),
            )

        tools = []
        for tool in data["toolsParams"]:
            tools.append(
                Tool(
                    name=tool["name"],
                    placeholders=tool["params"],
                ),
            )

        prompts.append(
            PromptCodegen(
                id=prompt.id,
                major_version=major,
                params=params,
                templates=sorted(templates, key=lambda t: t.snake_case_id),
                tools=sorted(tools, key=lambda t: t.snake_case_name),
            )
        )

    return sorted(prompts, key=lambda p: p.title_case_id)


def generate_code_for_config(config: AutogeneratePromptsConfig) -> str:
    prompts = make_prompts_from_config(config)

    auto = [HEADER]

    for prompt in prompts:
        auto.append(generate_code_for_prompt(prompt))

    return "\n".join(auto).strip() + "\n"


def write_generated_code_for_config(config: AutogeneratePromptsConfig) -> None:
    """Write generated code to outfile."""
    with open(config.outfile, "w") as f:
        f.write(generate_code_for_config(config))
