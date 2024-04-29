from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Literal
from typing import Union


@dataclass
class RemoteConfigResponse:
    id: str
    version: str
    value: Dict[str, Any]


@dataclass
class LatestRemoteConfig:
    id: str
    latest: Literal[True]


@dataclass
class RemoteConfigWithVersion:
    id: str
    version: str


@dataclass
class LatestDangerouslyUseUndeployed:
    latest: Literal[True]


@dataclass
class DangerouslyUseUndeployedWithRevision:
    revisionId: str


@dataclass
class DangerouslyUseUndeployedRemoteConfig:
    id: str
    dangerouslyUseUndeployed: Union[LatestDangerouslyUseUndeployed, DangerouslyUseUndeployedWithRevision]


RemoteConfig = Union[LatestRemoteConfig, RemoteConfigWithVersion, DangerouslyUseUndeployedRemoteConfig]
