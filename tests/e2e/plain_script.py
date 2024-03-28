import logging
import sys

from autoblocks.tracer import AutoblocksTracer
from tests.e2e.slow_evaluators import SlowEvaluator1
from tests.e2e.slow_evaluators import SlowEvaluator2

log = logging.getLogger(__name__)

tracer = AutoblocksTracer()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s %(asctime)s [%(levelname)s] %(message)s",
    )

    trace_id = sys.argv[1]
    sleep_seconds = int(sys.argv[2])

    log.info(f"Sending event with trace ID {trace_id}")
    tracer.send_event(
        "e2e-test-event-plain-script",
        trace_id=trace_id,
        properties=dict(
            sleep_seconds=sleep_seconds,
        ),
        evaluators=[SlowEvaluator1(), SlowEvaluator2()],
    )
    log.info("Event fired")
