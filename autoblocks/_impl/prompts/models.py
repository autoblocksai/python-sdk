import functools
import random
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union

from autoblocks._impl.prompts.placeholders import TemplatePlaceholder
from autoblocks._impl.prompts.placeholders import parse_placeholders_from_template

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

    @functools.cached_property
    def placeholders(self) -> List[TemplatePlaceholder]:
        return parse_placeholders_from_template(self.template)


class Prompt(FrozenModel):
    """A schema representing a prompt managed in the Autoblocks platform."""

    id: str
    version: str
    revision_id: str = pydantic.Field(..., alias="revisionId")
    params: Optional[PromptParams] = None
    templates: List[PromptTemplate]
    tools: Optional[List[Dict[str, Any]]] = None

    @functools.cached_property
    def tracking(self) -> dict[str, Any]:
        """
        Returns the schema expected by our ingestion endpoint's prompt tracking property.
        """
        return self.model_dump(by_alias=True)


class WeightedMinorVersion(FrozenModel):
    version: str
    weight: float = pydantic.Field(..., gt=0)


class PromptMinorVersion(FrozenModel):
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

    @functools.cached_property
    def all_minor_versions(self) -> Set[str]:
        versions: Set[str] = set()
        if weighted_versions := self.weighted_versions:
            for v in weighted_versions:
                versions.add(v.version)
        elif str_version := self.str_version:
            versions.add(str_version)
        return versions

    def choose_version(self) -> str:
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


class AutogeneratePromptConfig(FrozenModel):
    model_config = pydantic.ConfigDict(coerce_numbers_to_str=True)

    id: str
    major_version: Optional[str] = None
    dangerously_use_undeployed_revision: Optional[str] = None


class AutogeneratePromptsConfig(FrozenModel):
    outfile: str
    prompts: List[AutogeneratePromptConfig]
