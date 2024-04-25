import functools
import random
from enum import Enum
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Set
from typing import TypeVar
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
    model_config = pydantic.ConfigDict(frozen=True)


class PromptParams(FrozenModel):
    """LLM model parameters for a prompt."""

    params: Optional[Dict[str, Any]]


class PromptTemplate(FrozenModel):
    """An individual template for a prompt."""

    id: str
    template: str


class Prompt(FrozenModel):
    """A schema representing a prompt managed in the Autoblocks platform."""

    id: str
    version: str
    params: Optional[PromptParams] = None
    templates: List[PromptTemplate]

    @functools.cached_property
    def tracking(self) -> dict[str, Any]:
        """
        Returns the schema expected by our ingestion endpoint's prompt tracking property.
        """
        return self.model_dump()


MinorVersionEnumType = TypeVar("MinorVersionEnumType", bound=Enum)


class WeightedMinorVersion(
    FrozenModel,
    Generic[MinorVersionEnumType],
):
    version: MinorVersionEnumType
    weight: float = pydantic.Field(..., gt=0)

    @property
    def str_version(self) -> str:
        return str(self.version.value)


class PromptMinorVersion(FrozenModel):
    # need to do more research here, WeightedMinorVersion requires generics but we don't care what it is in this case,
    # just that it's an instance of WeightedMinorVersion.
    version: Union[str, Enum, List[WeightedMinorVersion]]  # type: ignore

    @property
    def str_version(self) -> Optional[str]:
        if isinstance(self.version, list):
            return None
        if isinstance(self.version, Enum):
            return str(self.version.value)
        return self.version

    @property
    def weighted_versions(self) -> Optional[List[WeightedMinorVersion]]:  # type: ignore
        if isinstance(self.version, list):
            return self.version
        return None

    @functools.cached_property
    def all_minor_versions(self) -> Set[str]:
        versions: Set[str] = set()
        if weighted_versions := self.weighted_versions:
            for v in weighted_versions:
                versions.add(v.str_version)
        elif str_version := self.str_version:
            versions.add(str_version)
        return versions

    def choose_version(self) -> str:
        if weighted_versions := self.weighted_versions:
            # Minor version is a weighted list; choose one according
            # to their weights.
            (rand_str_version,) = random.choices(
                population=[v.str_version for v in weighted_versions],
                weights=[v.weight for v in weighted_versions],
                k=1,
            )
            return rand_str_version
        elif str_version := self.str_version:
            # Minor version is a constant; return it.
            return str_version

        raise RuntimeError("Minor version should either be a string or a list of weighted versions.")


class AutogeneratePromptConfig(FrozenModel):
    id: str
    major_versions: List[str]

    @pydantic.field_validator("major_versions", mode="before")
    @classmethod
    def validate_and_transform_versions(cls, raw: List[Any]) -> List[str]:
        assert isinstance(raw, list), "major_versions must be a list"
        return [str(v) for v in raw]


class AutogeneratePromptsConfig(FrozenModel):
    outfile: str
    prompts: List[AutogeneratePromptConfig]
