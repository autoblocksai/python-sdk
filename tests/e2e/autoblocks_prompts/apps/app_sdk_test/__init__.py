# Auto-generated prompt module for app: app-sdk-test
from typing import Any
from typing import Optional

from . import prompts


def prompt_basic_prompt_manager(
    major_version: Optional[str] = None,
    minor_version: str = "0",
    api_key: Optional[str] = None,
    init_timeout: Optional[float] = None,
    refresh_timeout: Optional[float] = None,
    refresh_interval: Optional[float] = None,
) -> Any:
    return prompts.PromptBasicFactory.create(
        major_version=major_version,
        minor_version=minor_version,
        api_key=api_key,
        init_timeout=init_timeout,
        refresh_timeout=refresh_timeout,
        refresh_interval=refresh_interval,
    )
