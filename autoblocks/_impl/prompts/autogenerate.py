import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.models import AutogeneratePromptsConfig
from autoblocks._impl.prompts.models import FrozenModel
from autoblocks._impl.util import AutoblocksEnvVar


class TemplateParam(FrozenModel):
    name: str

    @property
    def snake_case_name(self) -> str:
        return to_snake_case(self.name)


class Template(FrozenModel):
    id: str
    params: List[TemplateParam]

    @property
    def snake_case_id(self) -> str:
        return to_snake_case(self.id)


class PromptCodegen(FrozenModel):
    id: str
    major_version: str
    params: Dict[str, Any]
    templates: List[Template]

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
    def execution_context_class_name(self) -> str:
        return f"{self.title_case_id}ExecutionContext"

    @property
    def manager_class_name(self) -> str:
        return f"{self.title_case_id}PromptManager"


HEADER = """############################################################################
# This file was generated automatically by Autoblocks. Do not edit directly.
############################################################################

from typing import Union  # noqa: F401

import pydantic  # noqa: F401

from autoblocks.prompts.context import PromptExecutionContext
from autoblocks.prompts.manager import AutoblocksPromptManager
from autoblocks.prompts.models import FrozenModel
from autoblocks.prompts.renderer import TemplateRenderer

"""


def to_title_case(s: str) -> str:
    # Remove leading numbers
    s = re.sub(r"^\d+", "", s)
    # Replace all non-alphanumeric characters with underscores
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    # Replace all underscores with capital letter of next word
    return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), s)


def to_snake_case(s: str) -> str:
    # Remove leading numbers
    s = re.sub(r"^\d+", "", s)

    # Replace all non-alphanumeric characters with spaces
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s)

    # Replace spaces with underscores
    s = re.sub(r"\s+", "_", s)

    # Add underscores between camel case words
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)

    # Remove leading and trailing underscores
    s = s.strip("_")

    return s.lower()


def parse_template_params(template: str) -> List[str]:
    """
    Extracts placeholders from a string. Placeholders look like: {{ param }}
    """
    pattern = r"\{\{\s*(.*?)\s*\}\}"
    params = re.findall(pattern, template)
    return sorted(list(set(params)))


def infer_type(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return "str"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, (int, float)):
        # The default union mode in pydantic is "smart" mode,
        # which will use the most specific type possible.
        # https://docs.pydantic.dev/latest/concepts/unions/
        return "Union[float, int]"
    elif isinstance(value, list):
        if len(value) > 0:
            return f"list[{infer_type(value[0])}]"
    return None


def indent(times: int = 1, size: int = 4) -> str:
    return " " * size * times


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

    if template.params:
        # Require all params to be passed in as keyword arguments
        auto += f"{indent(2)}*,\n"

    for param in template.params:
        auto += f"{indent(2)}{param.snake_case_name}: str,\n"

    auto += f"{indent()}) -> str:\n"
    auto += f'{indent(2)}return self._render(\n{indent(3)}"{template.id}",\n'

    for param in template.params:
        auto += f"{indent(3)}{param.snake_case_name}={param.snake_case_name},\n"

    auto += f"{indent(2)})\n"

    return auto


def generate_template_renderer_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.template_renderer_class_name}(TemplateRenderer):\n"

    # Add name mapper class attribute
    # The name mapper maps the original template placeholder name
    # to the snake case name of the corresponding keyword argument
    name_mapper = {}
    for template in prompt.templates:
        for param in template.params:
            name_mapper[param.name] = param.snake_case_name

    if name_mapper:
        auto += f"{indent()}__name_mapper__ = {{\n"

        for key in sorted(name_mapper.keys()):
            auto += f'{indent(2)}"{key}": "{name_mapper[key]}",\n'

        auto += f"{indent()}}}\n\n"
    else:
        auto += f"{indent()}__name_mapper__ = {{}}\n\n"

    auto += "\n".join(generate_template_render_method_code(template) for template in prompt.templates)

    return auto


def generate_execution_context_class_code(prompt: PromptCodegen) -> str:
    auto = f"class {prompt.execution_context_class_name}(\n"
    auto += f"{indent()}PromptExecutionContext[\n"
    auto += f"{indent(2)}{prompt.params_class_name},\n"
    auto += f"{indent(2)}{prompt.template_renderer_class_name},\n"
    auto += f"{indent()}],\n"
    auto += "):\n"
    auto += f"{indent()}__params_class__ = {prompt.params_class_name}\n"
    auto += f"{indent()}__template_renderer_class__ = {prompt.template_renderer_class_name}\n"

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

        resp = httpx.get(
            url=f"{API_ENDPOINT}/prompts/{prompt.id}/major/{major}/minor/{minor}",
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
            template_params = [TemplateParam(name=name) for name in parse_template_params(template["template"])]
            templates.append(
                Template(
                    id=template_id,
                    params=sorted(template_params, key=lambda p: p.snake_case_name),
                ),
            )

        prompts.append(
            PromptCodegen(
                id=prompt.id,
                major_version=major,
                params=params,
                templates=sorted(templates, key=lambda t: t.snake_case_id),
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
