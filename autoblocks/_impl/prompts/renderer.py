import abc
import re
from typing import Any
from typing import Dict

from autoblocks._impl.prompts.models import Prompt

# Regular expression pattern for finding placeholders
# in templates
placeholder_pattern: re.Pattern[str] = re.compile(r"\{\{\s*(.*?)\s*\}\}")


class TemplateRenderer(abc.ABC):
    # Map of param names in template to the names of the corresponding kwargs
    __name_mapper__: Dict[str, str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name_mapper__ is None:
            raise ValueError(f"TemplateRenderer subclass {cls} must define __name_mapper__")

    def __init__(self, prompt: Prompt) -> None:
        self.__template_map = {template.id: template.template for template in prompt.templates}

    def _render(self, template_id: str, **kwargs: Any) -> str:
        def replace(match: re.Match[str]) -> str:
            param_name = match.group(1).strip()
            kwarg_name = self.__name_mapper__[param_name]
            return str(kwargs[kwarg_name])

        return re.sub(
            pattern=placeholder_pattern,
            repl=replace,
            string=self.__template_map[template_id],
        )
