import asyncio
import logging
import os
import urllib.parse
from concurrent.futures import Future
from enum import Enum
from typing import Any
from typing import Coroutine
from typing import Optional
from typing import Tuple
from typing import Union

log = logging.getLogger(__name__)


AnyTask = Union[asyncio.Task[Any], Future[Any]]


class StrEnum(str, Enum):
    def __str__(self) -> str:
        # https://stackoverflow.com/a/74440069
        return str.__str__(self)


class AutoblocksEnvVar(StrEnum):
    ALIGN_TEST_CASE_HASH = "AUTOBLOCKS_ALIGN_TEST_CASE_HASH"
    ALIGN_TEST_EXTERNAL_ID = "AUTOBLOCKS_ALIGN_TEST_EXTERNAL_ID"
    API_KEY = "AUTOBLOCKS_API_KEY"
    CLI_SERVER_ADDRESS = "AUTOBLOCKS_CLI_SERVER_ADDRESS"
    INGESTION_KEY = "AUTOBLOCKS_INGESTION_KEY"
    PROMPT_REVISIONS = "AUTOBLOCKS_PROMPT_REVISIONS"
    TRACER_THROW_ON_ERROR = "AUTOBLOCKS_TRACER_THROW_ON_ERROR"

    def get(self) -> Optional[str]:
        return os.environ.get(self.value)


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
