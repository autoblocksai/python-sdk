import random
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

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
    app_name: str = pydantic.Field(..., alias="appName")
    major_versions: List[MajorVersion] = pydantic.Field(..., alias="majorVersions")

    @property
    def is_undeployed(self) -> bool:
        """Check if this prompt has no deployed versions (empty major_versions list)."""
        return len(self.major_versions) == 0


class WeightedMinorVersion(FrozenModel):
    """Weighted minor version for A/B testing."""

    version: str
    weight: float = pydantic.Field(..., gt=0)


class PromptMinorVersion(FrozenModel):
    """Minor version configuration for a prompt."""

    version: Union[str, List[WeightedMinorVersion]]

    @property
    def str_version(self) -> Optional[str]:
        if isinstance(self.version, list):
            return None
        return self.version

    @property
    def weighted_versions(self) -> Optional[List[WeightedMinorVersion]]:
        if isinstance(self.version, list):
            return self.version
        return None

    @property
    def all_minor_versions(self) -> set[str]:
        versions: set[str] = set()
        if weighted_versions := self.weighted_versions:
            for v in weighted_versions:
                versions.add(v.version)
        elif str_version := self.str_version:
            versions.add(str_version)
        return versions

    def choose_version(self) -> str:
        """
        Choose a version based on weights.

        Returns:
            The chosen version string
        """
        if weighted_versions := self.weighted_versions:
            # Minor version is a weighted list; choose one according
            # to their weights.
            (rand_str_version,) = random.choices(
                population=[v.version for v in weighted_versions],
                weights=[v.weight for v in weighted_versions],
                k=1,
            )
            return rand_str_version
        elif str_version := self.str_version:
            # Minor version is a constant; return it.
            return str_version

        raise RuntimeError("Minor version should either be a string or a list of weighted versions.")
