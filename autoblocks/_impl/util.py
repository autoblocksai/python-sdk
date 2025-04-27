import asyncio
import logging
import os
import traceback
import urllib.parse
from concurrent.futures import Future
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Coroutine
from typing import Optional
from typing import Tuple
from typing import Union

import orjson
from cuid2 import cuid_wrapper

log = logging.getLogger(__name__)


AnyTask = Union[asyncio.Task[Any], Future[Any]]

cuid_generator = cuid_wrapper()


class StrEnum(str, Enum):
    def __str__(self) -> str:
        # https://stackoverflow.com/a/74440069
        return str.__str__(self)


class AutoblocksEnvVar(StrEnum):
    ALIGN_TEST_CASE_HASH = "AUTOBLOCKS_ALIGN_TEST_CASE_HASH"
    ALIGN_TEST_EXTERNAL_ID = "AUTOBLOCKS_ALIGN_TEST_EXTERNAL_ID"
    API_KEY = "AUTOBLOCKS_API_KEY"
    V2_API_KEY = "AUTOBLOCKS_V2_API_KEY"
    CLI_SERVER_ADDRESS = "AUTOBLOCKS_CLI_SERVER_ADDRESS"
    INGESTION_KEY = "AUTOBLOCKS_INGESTION_KEY"
    FILTERS_TEST_SUITES = "AUTOBLOCKS_FILTERS_TEST_SUITES"
    OVERRIDES_PROMPT_REVISIONS = "AUTOBLOCKS_OVERRIDES_PROMPT_REVISIONS"
    OVERRIDES_CONFIG_REVISIONS = "AUTOBLOCKS_OVERRIDES_CONFIG_REVISIONS"
    OVERRIDES_TESTS_AND_HASHES = "AUTOBLOCKS_OVERRIDES_TESTS_AND_HASHES"
    TRACER_THROW_ON_ERROR = "AUTOBLOCKS_TRACER_THROW_ON_ERROR"
    CI_TEST_RUN_BUILD_ID = "AUTOBLOCKS_CI_TEST_RUN_BUILD_ID"
    V2_CI_TEST_RUN_BUILD_ID = "AUTOBLOCKS_V2_CI_TEST_RUN_BUILD_ID"
    SLACK_WEBHOOK_URL = "AUTOBLOCKS_SLACK_WEBHOOK_URL"
    TEST_RUN_MESSAGE = "AUTOBLOCKS_TEST_RUN_MESSAGE"
    DISABLE_GITHUB_COMMENT = "AUTOBLOCKS_DISABLE_GITHUB_COMMENT"

    def get(self) -> Optional[str]:
        return os.environ.get(self.value)


class ThirdPartyEnvVar(StrEnum):
    OPENAI_API_KEY = "OPENAI_API_KEY"
    GITHUB_TOKEN = "GITHUB_TOKEN"

    def get(self) -> Optional[str]:
        return os.environ.get(self.value)


def is_ci() -> bool:
    return os.environ.get("CI") == "true"


def is_github_comment_disabled() -> bool:
    return AutoblocksEnvVar.DISABLE_GITHUB_COMMENT.get() == "1"


def encode_uri_component(s: str) -> str:
    """
    This should have the same behavior as encodeURIComponent from JS.

    https://stackoverflow.com/a/6618858
    """
    return urllib.parse.quote(s, safe="()*!.'")


async def all_settled(coroutines: list[Coroutine[Any, Any, Any]]) -> Tuple[Union[BaseException, Any]]:
    """
    Runs all the coroutines in parallel and waits for all of them to finish,
    regardless of whether they succeed or fail. Similar to Promise.allSettled.
    """
    # mypy error:
    # Returning Any from function declared to return "tuple[BaseException | Any]"  [no-any-return]
    return await asyncio.gather(*coroutines, return_exceptions=True)  # type: ignore


def get_running_loop() -> Optional[asyncio.AbstractEventLoop]:
    """
    Returns the currently-running event loop if there is one.
    """
    try:
        # Raises a RuntimeError if no loop is running
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def now_iso_8601() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_cli_running() -> bool:
    return AutoblocksEnvVar.CLI_SERVER_ADDRESS.get() is not None


def orjson_default(o: Any) -> Any:
    if hasattr(o, "model_dump_json") and callable(o.model_dump_json):
        # pydantic v2
        return orjson.loads(o.model_dump_json())
    elif hasattr(o, "json") and callable(o.json):
        # pydantic v1
        return orjson.loads(o.json())
    elif isinstance(o, Exception):
        return "".join(
            traceback.format_exception(
                type(o),
                o,
                o.__traceback__,
            )
        )
    raise TypeError


def serialize(value: Any) -> str:
    """
    Serializes an unknown value to a string.
    """
    try:
        return orjson.dumps(value, default=orjson_default).decode("utf-8")
    except Exception as e:
        log.debug(f"Failed to serialize value: {value}", exc_info=e)
        return "\\{\\}"
