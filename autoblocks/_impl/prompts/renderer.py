import abc
import re
from typing import Any
from typing import Dict

from autoblocks._impl.prompts.models import Prompt
from autoblocks._impl.prompts.placeholders import PLACEHOLDER_PATTERN
from autoblocks._impl.prompts.placeholders import make_placeholder_from_match


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
            placeholder = make_placeholder_from_match(match)
            if placeholder.is_escaped:
                # Remove escape character from escaped placeholder
                return match.group(0)[1:]
            kwarg_name = self.__name_mapper__[placeholder.name]
            return str(kwargs[kwarg_name])

        return re.sub(
            pattern=PLACEHOLDER_PATTERN,
            repl=replace,
            string=self.__template_map[template_id],
        )
