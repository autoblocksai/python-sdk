import asyncio
import logging
import threading
import time
from datetime import timedelta
from typing import Optional
from typing import Set

import httpx

from autoblocks._impl.util import AnyTask

log = logging.getLogger(__name__)

_started: bool = False
_background_thread: Optional[threading.Thread] = None
_background_event_loop: Optional[asyncio.AbstractEventLoop] = None
_client: Optional[httpx.AsyncClient] = None
_sync_client: Optional[httpx.Client] = None
_background_tasks: Set[AnyTask] = set()
_main_thread_has_finished: bool = False


def _run_event_loop(_event_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_event_loop)
    _event_loop.run_forever()


def flush(timeout: Optional[timedelta] = None) -> None:
    """
    Wait for all pending tasks to complete.
    """
    timeout_seconds = timeout.total_seconds() if timeout else 30

    log.debug("Flushing background tasks with timeout of % seconds.", timeout_seconds)
    if not _background_tasks:
        # Already empty
        log.debug("No background tasks to flush.")
        return

    start_time = time.perf_counter()
    log.debug("Waiting for %s background tasks to finish...", len(_background_tasks))
    while _background_tasks and (time.perf_counter() - start_time) < timeout_seconds:
        time.sleep(0.1)

    if _background_tasks:
        log.error(
            "Timed out waiting for background tasks to flush. % tasks left unfinished.",
            len(_background_tasks),
        )
    else:
        log.debug("Successfully flushed all background tasks.")


def _flush_and_shut_down_event_loop() -> None:
    """
    Flushes all background tasks and then shuts down the event loop.
    """
    flush()

    if _background_thread and _background_event_loop and _background_event_loop.is_running():
        # Stop the event loop (will cause run_forever to stop)
        log.debug("Stopping event loop")
        _background_event_loop.call_soon_threadsafe(_background_event_loop.stop)
        # Wait for the thread to finish (will happen when run_forever stops)
        log.debug("Waiting for background thread to finish")
        _background_thread.join()
        # Cancel all remaining tasks
        log.debug("Cancelling all remaining tasks")
        for task in asyncio.all_tasks(_background_event_loop):
            task.cancel()
        _background_event_loop.run_until_complete(_background_event_loop.shutdown_asyncgens())
        # Close the loop
        log.debug("Closing event loop")
        _background_event_loop.close()
        log.debug("Event loop closed")


def _main_shut_down_monitor_thread() -> None:
    """
    Start a thread that waits for the main thread to finish and
    then flushes + shuts down the event loop.

    See https://stackoverflow.com/a/63075281
    """
    main_thread = threading.main_thread()
    main_thread.join()

    # Used by the tracer to switch to the sync HTTP client
    # after the interpreter has shut down. Otherwise we'll get:
    # RuntimeError: cannot schedule new futures after interpreter shutdown
    # TODO: figure out how to keep the main thread alive while
    # we flush the tasks so that we don't need to switch to the
    # sync client. Users will also run into issues if their
    # evaluators try to schedule new futures during shutdown.
    global _main_thread_has_finished
    _main_thread_has_finished = True

    log.debug("Handling main thread shutdown")
    _flush_and_shut_down_event_loop()


def init() -> None:
    global _started, _background_thread, _background_event_loop, _client, _sync_client

    if _started:
        return

    _client = httpx.AsyncClient()

    _sync_client = httpx.Client()

    _background_event_loop = asyncio.new_event_loop()

    threading.Thread(target=_main_shut_down_monitor_thread).start()

    _background_thread = threading.Thread(
        target=_run_event_loop,
        args=(_background_event_loop,),
    )
    _background_thread.start()

    _started = True


def event_loop() -> asyncio.AbstractEventLoop:
    if not _background_event_loop:
        raise Exception("Event loop not initialized")
    return _background_event_loop


def http_client() -> httpx.AsyncClient:
    if not _client:
        raise Exception("HTTP client not initialized")
    return _client


def sync_http_client() -> httpx.Client:
    if not _sync_client:
        raise Exception("HTTP client not initialized")
    return _sync_client


def add_background_task(task: AnyTask) -> None:
    """
    Keep a strong reference to the task so that it isn't garbage collected.
    See https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    We also use this set to flush tasks on exit (i.e. wait for it to be empty)
    """
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def main_thread_has_finished() -> bool:
    return _main_thread_has_finished
