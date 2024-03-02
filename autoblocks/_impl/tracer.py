import asyncio
import atexit
import contextvars
import dataclasses
import inspect
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import TracerEvent
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import gather_with_max_concurrency

log = logging.getLogger(__name__)


@atexit.register
def _cleanup_tracer() -> None:
    bg_thread = global_state.background_thread()
    if bg_thread:
        bg_thread.join()


@dataclasses.dataclass()
class SendEventResponse:
    trace_id: Optional[str]


class AutoblocksTracer:
    def __init__(
        self,
        ingestion_key: Optional[str] = None,
        # Initialize the tracer with a trace_id. All events sent with this tracer will
        # send this trace ID unless overwritten by:
        # - calling set_trace_id
        # - specifying a trace_id when calling send_event
        trace_id: Optional[str] = None,
        # Initialize the tracer with properties. All events sent with this tracer will
        # send these properties unless overwritten by:
        # - calling set_properties
        # Additionally, these properties can be updated by:
        # - calling update_properties
        # - specifying properties when calling send_event
        properties: Optional[Dict[Any, Any]] = None,
        # Timeout for sending events to Autoblocks
        timeout: timedelta = timedelta(seconds=5),
    ):
        global_state.init()  # Start up event loop if not already started
        self._trace_id: Optional[str] = trace_id
        self._properties: Dict[Any, Any] = properties or {}

        ingestion_key = ingestion_key or AutoblocksEnvVar.INGESTION_KEY.get()
        if not ingestion_key:
            raise ValueError(
                f"You must provide an ingestion_key or set the {AutoblocksEnvVar.INGESTION_KEY} environment variable."
            )

        self._client_headers = {"Authorization": f"Bearer {ingestion_key}"}
        self._timeout_seconds = timeout.total_seconds()

    def set_trace_id(self, trace_id: str) -> None:
        """
        Set the trace ID for all events sent by this tracer.
        """
        self._trace_id = trace_id

    @property
    def trace_id(self) -> Optional[str]:
        """
        Get the trace ID currently set on the tracer.
        """
        return self._trace_id

    def set_properties(self, properties: Dict[Any, Any]) -> None:
        """
        Set the properties for all events sent by this tracer.

        NOTE: This will overwrite any existing properties.
        """
        self._properties = properties

    def update_properties(self, properties: Dict[Any, Any]) -> None:
        """
        Update the properties for all events sent by this tracer.
        """
        self._properties.update(properties)

    @contextmanager
    def start_span(self) -> Generator[None, None, None]:
        props = dict(span_id=str(uuid.uuid4()))
        prev_span_id = self._properties.get("span_id")
        prev_parent_span_id = self._properties.get("parent_span_id")
        if prev_span_id:
            props["parent_span_id"] = prev_span_id
        self.update_properties(props)

        try:
            yield
        finally:
            props = dict(self._properties)
            props.pop("span_id", None)
            props.pop("parent_span_id", None)
            if prev_parent_span_id:
                props["parent_span_id"] = prev_parent_span_id
            if prev_span_id:
                props["span_id"] = prev_span_id
            self.set_properties(props)

    def _evaluation_to_json(self, evaluation: Evaluation, evaluator_external_id: str) -> Dict[str, Any]:
        return dict(
            id=str(uuid.uuid4()),
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
            metadata=evaluation.metadata,
            evaluatorExternalId=evaluator_external_id,
        )

    async def _evaluate_event(self, event: TracerEvent, evaluator: BaseEventEvaluator) -> Optional[Evaluation]:
        """
        Evaluates an event using a provided evaluator.
        """
        evaluation = None
        if inspect.iscoroutinefunction(evaluator.evaluate_event):
            try:
                evaluation = await evaluator.evaluate_event(event=event)
            except Exception as err:
                log.error(f"Unable to execute evaluator with id: {evaluator.id}. Error: %s", err, exc_info=True)
        else:
            try:
                ctx = contextvars.copy_context()
                evaluation = await global_state.event_loop().run_in_executor(
                    None,
                    ctx.run,
                    evaluator.evaluate_event,
                    event,
                )
            except Exception as err:
                log.error(f"Unable to execute evaluator with id: {evaluator.id}. Error: %s", err, exc_info=True)

        return evaluation

    async def _run_evaluators_unsafe(
        self, evaluators: List[BaseEventEvaluator], event: TracerEvent, max_evaluator_concurrency: int
    ) -> List[Dict[str, Any]]:
        if len(evaluators) == 0:
            return []
        evaluations: List[Evaluation] = await gather_with_max_concurrency(
            max_evaluator_concurrency,
            [
                self._evaluate_event(
                    event=event,
                    evaluator=evaluator,
                )
                for evaluator in evaluators
            ],
        )
        return [
            self._evaluation_to_json(evaluation=evaluation, evaluator_external_id=evaluator.id)
            for evaluator, evaluation in zip(evaluators, evaluations)
            if evaluation is not None
        ]

    async def _send_event_unsafe(
        self,
        # Require all arguments to be specified via key=value
        *,
        message: str,
        max_evaluator_concurrency: int,
        trace_id: Optional[str],
        span_id: Optional[str],
        parent_span_id: Optional[str],
        timestamp: Optional[str],
        properties: Optional[Dict[Any, Any]],
        prompt_tracking: Optional[Dict[str, Any]],
        evaluators: Optional[List[BaseEventEvaluator]],
    ) -> None:
        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})

        # Overwrite properties with any provided as top level arguments
        if span_id:
            merged_properties["span_id"] = span_id
        if parent_span_id:
            merged_properties["parent_span_id"] = parent_span_id
        if prompt_tracking:
            merged_properties["promptTracking"] = prompt_tracking
        trace_id = trace_id or self._trace_id
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        # If there are evaluators, run them and compute the evaluations property
        if evaluators:
            try:
                evaluations = await self._run_evaluators_unsafe(
                    event=TracerEvent(
                        message=message,
                        trace_id=trace_id,
                        timestamp=timestamp,
                        properties=merged_properties,
                    ),
                    evaluators=evaluators,
                    max_evaluator_concurrency=max_evaluator_concurrency,
                )
                if evaluations:
                    # Update merged properties with computed evaluations property
                    merged_properties["evaluations"] = evaluations
            except Exception as err:
                log.error("Unable to evaluate events. Error: %s", err, exc_info=True)

        traced_event = TracerEvent(
            message=message,
            trace_id=trace_id,
            timestamp=timestamp,
            properties=merged_properties,
        )
        req = global_state.sync_http_client().post(
            url=INGESTION_ENDPOINT,
            json=traced_event.to_json(),
            headers=self._client_headers,
            timeout=self._timeout_seconds,
        )
        req.raise_for_status()

    def send_event(
        self,
        message: str,
        # Require all arguments after message to be specified via key=value
        *,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        evaluators: Optional[List[BaseEventEvaluator]] = None,
        max_evaluator_concurrency: int = 5,
        prompt_tracking: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Sends an event to the Autoblocks ingestion API.

        Always returns a SendEventResponse dataclass as the response. If sending
        the event failed, the trace_id will be None.
        """
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_event_unsafe(
                    message=message,
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    timestamp=timestamp,
                    properties=properties,
                    evaluators=evaluators,
                    max_evaluator_concurrency=max_evaluator_concurrency,
                    prompt_tracking=prompt_tracking,
                ),
                global_state.event_loop(),
            )
            if AutoblocksEnvVar.TRACER_BLOCK_ON_SEND_EVENT.get() == "1":
                future.result()
        except Exception as err:
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            if AutoblocksEnvVar.TRACER_THROW_ON_ERROR.get() == "1":
                raise err
