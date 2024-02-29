# Write a main function that sends an event using the autoblocks tracer
import asyncio
import sys
import time

from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.models import TracerEvent
from autoblocks.tracer import AutoblocksTracer

tracer = AutoblocksTracer()


# Send an event using the autoblocks tracer
class MyEvaluator(BaseEventEvaluator):
    id = "e2e-test-evaluator"

    async def evaluate_event(self, event: TracerEvent) -> Evaluation:
        await asyncio.sleep(1)
        return Evaluation(
            score=0.9,
            threshold=Threshold(gte=0.5),
        )


def main():
    trace = sys.argv[1]
    tracer.send_event("tracer_shutdown", trace_id=str(trace), evaluators=[MyEvaluator()])
    time.sleep(10)  # Sleep for 10 seconds to allow time for signal to be sent


if __name__ == "__main__":
    main()
