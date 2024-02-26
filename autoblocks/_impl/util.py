import asyncio
import logging
import os
import urllib.parse
from enum import Enum
from typing import Coroutine
from typing import List
from typing import Optional

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


async def gather_with_max_concurrency(
    max_concurrency: int,
    coroutines: List[Coroutine],
) -> asyncio.Future[list]:
    """
    Borrowed from https://stackoverflow.com/a/61478547
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_coro(coro: Coroutine):
        async with semaphore:
            return await coro

    # return_exceptions=True causes exceptions to be returned as values instead
    # of propagating them to the caller. this is similar in behavior to Promise.allSettled
    return await asyncio.gather(*(sem_coro(c) for c in coroutines), return_exceptions=True)
