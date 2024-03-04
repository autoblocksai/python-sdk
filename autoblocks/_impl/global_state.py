import asyncio
import atexit
import logging
import signal
import threading
from typing import Optional

import httpx

from autoblocks._impl.util import SEND_EVENT_CORO_NAME

log = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_started: bool = False
_event_loop_shutdown_lock = asyncio.Semaphore(1)


def init() -> None:
    global _client, _loop, _started

    if _started:
        return

    _client = httpx.AsyncClient()

    _loop = asyncio.new_event_loop()

    for s in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
        _loop.add_signal_handler(
            s,
            lambda *args, **kwargs: asyncio.create_task(_shutdown_event_loop_at_signal()),
        )

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


async def _shutdown_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    async with _event_loop_shutdown_lock:
        tasks_to_wait_for = []
        for task in asyncio.all_tasks() - {asyncio.current_task()}:
            coro_name = task.get_coro().__name__  # type: ignore
            if coro_name == SEND_EVENT_CORO_NAME:
                tasks_to_wait_for.append(task)

        log.info(f"Waiting for {len(tasks_to_wait_for)} tasks to resolve")
        await asyncio.gather(*tasks_to_wait_for, return_exceptions=True)
        log.info("All tasks resolved")
        log.info("Stopping event loop")
        loop.stop()
        log.info("Event loop stopped")


async def _shutdown_event_loop_at_signal() -> None:
    while _loop and _loop.is_running() and not _event_loop_shutdown_lock.locked():
        try:
            await _shutdown_event_loop(_loop)
        except Exception:
            pass


@atexit.register
def _shutdown_event_loop_at_exit() -> None:
    while _loop and _loop.is_running() and not _event_loop_shutdown_lock.locked():
        try:
            asyncio.run_coroutine_threadsafe(_shutdown_event_loop(_loop), _loop)
        except Exception:
            pass


def event_loop() -> asyncio.AbstractEventLoop:
    if not _loop:
        raise Exception("Event loop not initialized")
    return _loop


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client
