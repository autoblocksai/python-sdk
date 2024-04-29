from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Optional


@dataclass
class RemoteConfigResponse:
    id: str
    version: str
    value: Dict[str, Any]


@dataclass
class RemoteConfig:
    id: str
    # only one of these should be specified
    version: Optional[str] = None  # can be a version like "1" or "latest"
    dangerously_use_undeployed_revision: Optional[str] = None  # can be a specific revision id or "latest"
