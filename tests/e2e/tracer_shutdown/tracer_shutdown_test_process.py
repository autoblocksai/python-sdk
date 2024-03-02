# Write a main function that sends an event using the autoblocks tracer
import asyncio
import signal
import sys

from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.models import TracerEvent
from autoblocks.tracer import AutoblocksTracer

tracer = AutoblocksTracer()


# Send an event using the autoblocks tracer
class MyEvaluator(BaseEventEvaluator):
    id = "e2e-test-evaluator"

    async def evaluate_event(self, event: TracerEvent) -> Evaluation:  # type: ignore
        await asyncio.sleep(10)
        return Evaluation(
            score=0.9,
            threshold=Threshold(gte=0.5),
        )


_running = True


def signal_handler(sig, frame):
    global _running
    _running = False


def main():
    signal.signal(signal.SIGINT, signal_handler)
    trace = sys.argv[1]
    tracer.send_event("tracer_shutdown", trace_id=str(trace), evaluators=[MyEvaluator()])
    while True:
        if not _running:
            break
    print("Exiting")


if __name__ == "__main__":
    main()
