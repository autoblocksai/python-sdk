import asyncio
import logging
import signal
import threading
from typing import Optional

import httpx

log = logging.getLogger(__name__)

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
        target=_run_event_loop,
        args=(_loop,),
        daemon=True,
    )
    background_thread.start()
    signal.signal(signal.SIGTERM, _on_unexpected_exit)
    signal.signal(signal.SIGINT, _on_unexpected_exit)
    _started = True


def _on_unexpected_exit(signum, frame):
    if _loop and _loop.is_running():
        log.info(f"Attempting to gracefully stop event loop. Received signal {signum}")
        _loop.stop()
        _loop.close()
    exit(0)


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
