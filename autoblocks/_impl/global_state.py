import asyncio
import threading
from typing import Optional

import httpx

_client: Optional[httpx.AsyncClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_started: bool = False


def init() -> None:
    global _client, _loop, _started

    if _started:
        return

    _client = httpx.AsyncClient()

    _loop = asyncio.new_event_loop()

    background_thread = threading.Thread(
        target=run_event_loop,
        args=(_loop,),
        daemon=True,
    )
    background_thread.start()

    _started = True


def run_event_loop(event_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()


def event_loop() -> asyncio.AbstractEventLoop:
    if not _loop:
        raise Exception("Event loop not initialized")
    return _loop


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client
