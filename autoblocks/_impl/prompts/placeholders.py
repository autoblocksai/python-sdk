import dataclasses
import re
from typing import List


@dataclasses.dataclass(eq=True, order=True, frozen=True)  # make the dataclass hashable and sortable
class TemplatePlaceholder:
    name: str  # the name of the placeholder (the text between the curly braces)
    is_escaped: bool  # true if this placeholder is preceded by an escape character


# Regular expression pattern for finding placeholders in templates
# Has two groups: the first is an optional backslash escape, the second is the placeholder name
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"(\\?)\{\{\s*([\w-]+)\s*\}\}")


def make_placeholder_from_match(match: re.Match[str]) -> TemplatePlaceholder:
    is_escaped, name = match.groups()
    return TemplatePlaceholder(
        name=name,
        # the placeholder is escaped if the first group is defined
        is_escaped=bool(is_escaped),
    )


def parse_placeholders_from_template(template: str) -> List[TemplatePlaceholder]:
    """
    Extracts placeholders from a template string. Placeholders look like: {{ param }}

    Placeholders can be escaped with a leading backslash: \\{{ escaped }}
    """
    placeholders = [make_placeholder_from_match(match) for match in PLACEHOLDER_PATTERN.finditer(template)]
    return sorted(set(placeholders))
