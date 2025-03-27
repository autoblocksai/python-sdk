from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


@dataclass
class VersionConfig:
    """Configuration for generating code for a specific prompt version."""

    title_case_id: str
    version: str
    prompt_id: str
    app_id: str
    params: Dict[str, Any]
    templates: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]


@dataclass
class PromptData:
    """Container for prompt data, handling both deployed and undeployed cases."""

    id: str
    app_id: str
    app_name: str
    is_undeployed: bool
    major_versions: List[Dict[str, Any]]
    undeployed_data: Optional[Dict[str, Any]] = None


# Type alias for app map structure
AppData = Dict[str, Any]
