import asyncio
import logging
import os
import urllib.parse
from enum import Enum
from typing import Any
from typing import Coroutine
from typing import Optional
from typing import Tuple
from typing import Union

log = logging.getLogger(__name__)


class StrEnum(str, Enum):
    def __str__(self) -> str:
        # https://stackoverflow.com/a/74440069
        return str.__str__(self)


class AutoblocksEnvVar(StrEnum):
    API_KEY = "AUTOBLOCKS_API_KEY"
    CLI_SERVER_ADDRESS = "AUTOBLOCKS_CLI_SERVER_ADDRESS"
    INGESTION_KEY = "AUTOBLOCKS_INGESTION_KEY"
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
