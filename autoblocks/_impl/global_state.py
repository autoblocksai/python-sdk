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
    for sig in [signal.SIGINT, signal.SIGTERM]:
        _loop.add_signal_handler(sig, lambda: asyncio.ensure_future(_on_exist_signal()))
    _started = True


async def _on_exist_signal() -> None:
    if _loop:
        # Ignore type below - accessing __name__ on coro which mypy doesn't like
        tasks = [
            x for x in asyncio.all_tasks(loop=_loop) if x.get_coro().__name__ == "_send_event_unsafe" and not x.done()  # type: ignore
        ]
        logging.info(f"Attempting to flush f{len(tasks)} outstanding send event tasks")
        await asyncio.gather(*tasks)
        log.info("Stopping event loop")
        _loop.stop()


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
