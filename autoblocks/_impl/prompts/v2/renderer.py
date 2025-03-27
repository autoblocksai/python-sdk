import abc
import json
import re
from typing import Any
from typing import Dict

from autoblocks._impl.prompts.placeholders import PLACEHOLDER_PATTERN
from autoblocks._impl.prompts.placeholders import make_placeholder_from_match


class TemplateRenderer(abc.ABC):
    """Base class for template renderers in V2."""

    # Map of placeholder names in template to the names of the corresponding kwargs
    __name_mapper__: Dict[str, str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name_mapper__ is None:
            raise ValueError(f"TemplateRenderer subclass {cls} must define __name_mapper__")

    def __init__(self, templates: Dict[str, str]) -> None:
        self.__template_map = templates

    def _render(self, template_id: str, **kwargs: Any) -> str:
        """
        Render a template with the given kwargs.

        Args:
            template_id: The ID of the template to render
            **kwargs: The values to substitute for placeholders

        Returns:
            The rendered template
        """

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


class ToolRenderer(abc.ABC):
    """Base class for tool renderers in V2."""

    # Map of placeholder names in tool to the names of the corresponding kwargs
    __name_mapper__: Dict[str, str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name_mapper__ is None:
            raise ValueError(f"ToolRenderer subclass {cls} must define __name_mapper__")

    def __init__(self, tools: Dict[str, Dict[str, Any]]) -> None:
        self.__tool_map = tools

    def _render(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Render a tool with the given kwargs.

        Args:
            tool_name: The name of the tool to render
            **kwargs: The values to substitute for placeholders

        Returns:
            The rendered tool as a dictionary
        """

        def replace(match: re.Match[str]) -> str:
            placeholder = make_placeholder_from_match(match)
            if placeholder.is_escaped:
                # Remove escape character from escaped placeholder
                return match.group(0)[1:]
            kwarg_name = self.__name_mapper__[placeholder.name]
            return str(kwargs[kwarg_name])

        # Convert tool to a string to easily replace placeholders
        tool_as_string = json.dumps(self.__tool_map[tool_name])
        replaced = re.sub(pattern=PLACEHOLDER_PATTERN, repl=replace, string=tool_as_string)

        # Convert back to a dictionary with replaced placeholders
        return json.loads(replaced)  # type: ignore
