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


class HeadlessPromptParams(FrozenModel):
    """LLM model parameters for a prompt."""

    version: str
    params: Dict[str, Any]


class HeadlessPromptTemplate(FrozenModel):
    """An individual template for a prompt."""

    id: str
    version: str
    template: str


class HeadlessPrompt(FrozenModel):
    """A prompt managed in the Autoblocks platform."""

    id: str
    version: str
    params: Optional[HeadlessPromptParams] = None
    templates: List[HeadlessPromptTemplate]

    @property
    def major_version(self) -> str:
        return self.version.split(".")[0]

    @property
    def minor_version(self) -> str:
        return self.version.split(".")[1]


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
    version: Union[Enum, List[WeightedMinorVersion]]

    @property
    def str_version(self) -> Optional[str]:
        if isinstance(self.version, list):
            return None
        return str(self.version.value)

    @property
    def weighted_versions(self) -> Optional[List[WeightedMinorVersion]]:
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

    def random_version(self) -> str:
        if weighted_versions := self.weighted_versions:
            (rand_str_version,) = random.choices(
                population=[v.str_version for v in weighted_versions],
                weights=[v.weight for v in weighted_versions],
                k=1,
            )
            return rand_str_version
        elif str_version := self.str_version:
            return str_version


class AutogeneratePromptConfig(FrozenModel):
    id: str
    major_versions: List[int]

    def major_versions_as_str(self) -> List[str]:
        return [str(v) for v in self.major_versions]


class AutogeneratePromptsConfig(FrozenModel):
    outfile: str
    prompts: List[AutogeneratePromptConfig]
