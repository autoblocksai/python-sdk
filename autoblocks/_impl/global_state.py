import asyncio
import logging
import signal
import threading
from typing import Optional

import httpx

from autoblocks._impl.util import SEND_EVENT_CORO_NAME

log = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_background_thread: Optional[threading.Thread] = None
_started: bool = False


def init() -> None:
    global _client, _loop, _started, _background_thread

    if _started:
        return

    _client = httpx.AsyncClient()

    _loop = asyncio.new_event_loop()

    for s in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
        _loop.add_signal_handler(
            s,
            lambda *args, **kwargs: asyncio.create_task(_shutdown_event_loop(s, _loop)),
        )

    _background_thread = threading.Thread(
        target=_run_event_loop,
        args=(_loop,),
        daemon=True,
    )
    _background_thread.start()

    _started = True


def _run_event_loop(_event_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_event_loop)
    _event_loop.run_forever()


async def _shutdown_event_loop(sig: int, loop: asyncio.AbstractEventLoop) -> None:
    log.info(f"Gracefully shutting down event loop after receiving signal {sig}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    event_tasks = []
    for task in tasks:
        coro_name = task.get_coro().__name__  # type: ignore
        if coro_name == SEND_EVENT_CORO_NAME:
            event_tasks.append(task)

    log.info(f"Waiting for {len(event_tasks)} outstanding events to be sent")
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("All events sent")
    log.info("Stopping event loop")
    loop.stop()
    log.info("Event loop stopped")


def event_loop() -> asyncio.AbstractEventLoop:
    if not _loop:
        raise Exception("Event loop not initialized")
    return _loop


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client
