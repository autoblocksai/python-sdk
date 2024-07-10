import asyncio
import logging
import sys

from autoblocks.tracer import AutoblocksTracer
from autoblocks.tracer import flush
from tests.e2e.test_e2e import E2E_TESTS_EXPECTED_MESSAGE

log = logging.getLogger(__name__)

tracer = AutoblocksTracer()


async def my_send_event() -> None:
    trace_id = sys.argv[1]
    sleep_seconds = int(sys.argv[2])
    log.info(f"Sending event with trace ID {trace_id}")
    tracer.send_event(
        E2E_TESTS_EXPECTED_MESSAGE,
        trace_id=trace_id,
        properties=dict(
            sleep_seconds=sleep_seconds,
        ),
        evaluators=[],
    )
    log.info("Event fired")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s %(asctime)s [%(levelname)s] %(message)s",
    )
    asyncio.run(my_send_event())
    # Currently have to call flush manually
    # because of a race condition in our logic to check if the main thread has finished
    flush()
