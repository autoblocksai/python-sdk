from dataclasses import dataclass
from typing import Any
from typing import List
from typing import Optional

try:
    import pydantic

    assert pydantic.__version__.startswith("2.")
except (ImportError, AssertionError):
    raise ImportError(
        "The Autoblocks config SDK requires pydantic version 2.x. "
        "You can install it with `pip install pydantic==2.*`."
    )


class FrozenModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)


class Property(FrozenModel):
    id: str
    value: Any


class RemoteConfigResponse(FrozenModel):
    id: str
    version: str
    revision_id: str = pydantic.Field(..., alias="revisionId")
    properties: List[Property]


@dataclass
class RemoteConfig:
    id: str
    # only one of these should be specified
    major_version: Optional[str] = None  # should be a specific major version
    minor_version: Optional[str] = None  # should be a specific minor version or "latest"
    dangerously_use_undeployed_revision: Optional[str] = None  # can be a specific revision id or "latest"
