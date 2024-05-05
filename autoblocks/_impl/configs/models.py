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
    name: str
    value: Any


class RemoteConfigResponse(FrozenModel):
    id: str
    version: str
    properties: List[Property]


@dataclass
class RemoteConfig:
    id: str
    # only one of these should be specified
    major_version: Optional[int] = None  # should be a sepcific major version
    minor_version: Optional[int] = None  # omitted for latest minor version
    dangerously_use_undeployed_revision: Optional[str] = None  # can be a specific revision id or "latest"
