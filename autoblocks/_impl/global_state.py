import asyncio
import logging
import threading
from typing import Optional

import httpx

log = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None
_sync_client: Optional[httpx.Client] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_started: bool = False


def init() -> None:
    global _client, _loop, _started, _sync_client

    if _started:
        return

    _client = httpx.AsyncClient()

    _sync_client = httpx.Client()

    _loop = asyncio.new_event_loop()

    background_thread = threading.Thread(
        target=_run_event_loop,
        args=(_loop,),
        daemon=True,
    )
    background_thread.start()
    _started = True


def _run_event_loop(_event_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_event_loop)
    _event_loop.run_forever()


def event_loop() -> asyncio.AbstractEventLoop:
    if not _loop:
        raise Exception("Event loop not initialized")
    return _loop


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client


def sync_http_client() -> httpx.Client:
    if not _sync_client:
        raise Exception("HTTP client not initialized")
    return _sync_client
