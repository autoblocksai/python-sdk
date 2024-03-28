import abc
import asyncio
import logging

from autoblocks.testing.models import BaseEventEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.models import Threshold
from autoblocks.testing.models import TracerEvent

log = logging.getLogger(__name__)


class SlowEvaluator(BaseEventEvaluator, abc.ABC):
    async def evaluate_event(self, event: TracerEvent) -> Evaluation:
        log.info(f"[{self.id}] Evaluating event {event.trace_id}")
        sleep_seconds = event.properties["sleep_seconds"]

        while sleep_seconds:
            log.info(f"[{self.id}] {sleep_seconds} seconds left")
            await asyncio.sleep(1)
            sleep_seconds -= 1

        log.info(f"[{self.id}] Done evaluating event {event.trace_id}")

        return Evaluation(
            score=1,
            threshold=Threshold(gte=0.5),
        )


class SlowEvaluator1(SlowEvaluator):
    id = "e2e-slow-evaluator-1"


class SlowEvaluator2(SlowEvaluator):
    id = "e2e-slow-evaluator-2"
