import asyncio
import logging

from flask import Flask
from flask import request

from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.models import TracerEvent
from autoblocks.tracer import AutoblocksTracer

log = logging.getLogger(__name__)

tracer = AutoblocksTracer()

app = Flask(__name__)


class MyEvaluator(BaseEventEvaluator):
    id = "e2e-test-evaluator"

    async def evaluate_event(self, event: TracerEvent) -> Evaluation:
        await asyncio.sleep(8)
        return Evaluation(
            score=0.9,
            threshold=Threshold(gte=0.5),
        )


@app.route("/", methods=["POST"])
def index():
    trace_id = request.json["trace_id"]
    log.info(f"Sending event with trace ID {trace_id}")
    tracer.send_event("tracer_shutdown", trace_id=trace_id, evaluators=[MyEvaluator()])
    log.info("Event fired")
    return "OK"
