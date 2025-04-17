from typing import Any
from typing import Dict
from typing import List
from typing import Optional

try:
    import pydantic

    assert pydantic.__version__.startswith("2.")
except (ImportError, AssertionError):
    raise ImportError(
        "The Autoblocks prompt SDK requires pydantic version 2.x. "
        "You can install it with `pip install pydantic==2.*`."
    )


class FrozenModel(pydantic.BaseModel):
    """Base model with frozen attributes for V2 prompts."""

    model_config = pydantic.ConfigDict(frozen=True)


class Template(FrozenModel):
    """Template for a V2 prompt."""

    id: str = pydantic.Field(..., alias="id")
    template: str = pydantic.Field(..., alias="template")


class ToolParams(FrozenModel):
    """Tool parameters for a V2 prompt."""

    name: str = pydantic.Field(..., alias="name")
    params: List[str] = pydantic.Field(..., alias="params")


class PromptParams(FrozenModel):
    """Parameters for a V2 prompt."""

    params: Optional[Dict[str, Any]] = pydantic.Field(None, alias="params")


class MajorVersion(FrozenModel):
    """Major version of a V2 prompt."""

    major_version: str = pydantic.Field(..., alias="majorVersion")
    minor_versions: List[str] = pydantic.Field(..., alias="minorVersions")
    templates: List[Template] = pydantic.Field(..., alias="templates")
    tools_params: Optional[List[ToolParams]] = pydantic.Field(None, alias="toolsParams")
    params: Optional[PromptParams] = pydantic.Field(None, alias="params")


class Prompt(FrozenModel):
    """A V2 prompt with its metadata."""

    id: str
    app_id: str = pydantic.Field(..., alias="appId")
    app_name: str = pydantic.Field(..., alias="slug")
    major_versions: List[MajorVersion] = pydantic.Field(..., alias="majorVersions")

    @property
    def is_undeployed(self) -> bool:
        """Check if this prompt has no deployed versions (empty major_versions list)."""
        return len(self.major_versions) == 0


class PromptMinorVersion(FrozenModel):
    """Minor version configuration for a prompt."""

    version: str
