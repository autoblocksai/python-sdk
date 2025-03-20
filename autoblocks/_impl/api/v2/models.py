import functools
from typing import Any, Dict, List, Optional

import pydantic

from autoblocks._impl.prompts.placeholders import TemplatePlaceholder
from autoblocks._impl.prompts.placeholders import parse_placeholders_from_template


class PromptTemplate(pydantic.BaseModel):
    """An individual template for a prompt in the V2 API."""
    id: str
    template: str

    @functools.cached_property
    def placeholders(self) -> List[TemplatePlaceholder]:
        """Parse and return all placeholders in the template."""
        return parse_placeholders_from_template(self.template)


class PromptMajorVersion(pydantic.BaseModel):
    """A major version of a prompt in the V2 API."""
    major_version: str
    minor_versions: List[str]
    templates: List[PromptTemplate]
    tools_params: Optional[List[Dict[str, Any]]] = None
    params: Optional[Dict[str, Any]] = None


class Prompt(pydantic.BaseModel):
    """A prompt in the V2 API."""
    id: str
    app_id: str
    major_versions: List[PromptMajorVersion]

    def get_major_version(self, version: str) -> Optional[PromptMajorVersion]:
        """Get a specific major version of the prompt."""
        for major_version in self.major_versions:
            if major_version.major_version == version:
                return major_version
        return None 