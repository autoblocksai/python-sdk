import logging

from flask import Flask
from flask import request

from autoblocks.tracer import AutoblocksTracer
from tests.e2e.slow_evaluators import SlowEvaluator1
from tests.e2e.slow_evaluators import SlowEvaluator2
from tests.e2e.test_e2e import E2E_TESTS_EXPECTED_MESSAGE

logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s %(asctime)s [%(levelname)s] %(message)s",
)

tracer = AutoblocksTracer()

app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    trace_id = request.json["trace_id"]  # type: ignore
    sleep_seconds = request.json["sleep_seconds"]  # type: ignore
    app.logger.info(f"Sending event with trace ID {trace_id}")
    tracer.send_event(
        E2E_TESTS_EXPECTED_MESSAGE,
        trace_id=trace_id,
        properties=dict(
            sleep_seconds=sleep_seconds,
        ),
        evaluators=[SlowEvaluator1(), SlowEvaluator2()],
    )
    app.logger.info("Event fired")
    return "OK"
