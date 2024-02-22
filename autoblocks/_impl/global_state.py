import asyncio
import threading
from typing import Coroutine
from typing import List
from typing import Optional

import httpx

_client: Optional[httpx.AsyncClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_started: bool = False


def init(client: httpx.AsyncClient) -> None:
    global _client, _loop, _started

    if _started:
        return

    _client = client

    _loop = asyncio.new_event_loop()

    background_thread = threading.Thread(
        target=run_event_loop,
        args=(_loop,),
        daemon=True,
    )
    background_thread.start()

    _started = True


def run_event_loop(_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def event_loop() -> asyncio.AbstractEventLoop:
    if not _loop:
        raise Exception("Event loop not initialized")
    return _loop


async def gather_with_max_concurrency(
    max_concurrency: int,
    coroutines: List[Coroutine],
) -> None:
    """
    Borrowed from https://stackoverflow.com/a/61478547
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_coro(coro: Coroutine):
        async with semaphore:
            return await coro

    # return_exceptions=True causes exceptions to be returned as values instead
    # of propagating them to the caller. this is similar in behavior to Promise.allSettled
    await asyncio.gather(*(sem_coro(c) for c in coroutines), return_exceptions=True)


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client


def started() -> bool:
    return _started
