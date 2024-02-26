import asyncio
import contextvars
import inspect
import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import EventEvaluation
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import gather_with_max_concurrency

log = logging.getLogger(__name__)


@dataclass
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
        properties: Optional[Dict] = None,
        # Timeout for sending events to Autoblocks
        timeout: timedelta = timedelta(seconds=5),
    ):
        global_state.init()  # Start up event loop if not already started
        self._trace_id: Optional[str] = trace_id
        self._properties: Dict = properties or {}

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

    def set_properties(self, properties: Dict) -> None:
        """
        Set the properties for all events sent by this tracer.

        NOTE: This will overwrite any existing properties.
        """
        self._properties = properties

    def update_properties(self, properties: Dict) -> None:
        """
        Update the properties for all events sent by this tracer.
        """
        self._properties.update(properties)

    @contextmanager
    def start_span(self):
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

    async def evaluate_event(self, event: Any, evaluator: BaseEventEvaluator) -> None:
        """
        Evaluates an event using a provided evaluator.
        """
        if inspect.iscoroutinefunction(evaluator.evaluate_event):
            try:
                evaluation = await evaluator.evaluate_event(event=event)
            except Exception:
                print("NEED TO LOG ERROR HERE")
        else:
            try:
                ctx = contextvars.copy_context()
                evaluation = await global_state.event_loop().run_in_executor(
                    None,
                    ctx.run,
                    evaluator.evaluate_event,
                    event,
                )
            except Exception:
                print("NEED TO LOG ERROR HERE")

        if evaluation is None:
            return
        return evaluation

    async def _send_event_unsafe(
        self,
        # Require all arguments to be specified via key=value
        *,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None,
        prompt_tracking: Optional[Dict] = None,
        evaluators: List[BaseEventEvaluator] = [],
        max_evaluator_concurrency: int,
    ) -> SendEventResponse:
        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})
        if span_id:
            merged_properties["span_id"] = span_id
        if parent_span_id:
            merged_properties["parent_span_id"] = parent_span_id
        if prompt_tracking:
            merged_properties["promptTracking"] = prompt_tracking

        trace_id = trace_id or self._trace_id
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        event_json = {
            "message": message,
            "traceId": trace_id,
            "timestamp": timestamp,
            "properties": merged_properties,
        }
        try:
            evaluations: List[EventEvaluation] = await gather_with_max_concurrency(
                max_evaluator_concurrency,
                [
                    self.evaluate_event(
                        event=event_json,
                        evaluator=evaluator,
                    )
                    for evaluator in evaluators
                ],
            )
            if evaluations and len(evaluations) > 0:
                # loop through each evaluations and build a dict containing externalEvaluationId as the key
                formatted_eval_json = [
                    dict(
                        externalEvaluationId=evaluation.evaluator_external_id,
                        id=str(evaluation.id),
                        score=evaluation.score,
                        metadata=dict(evaluation.metadata) if evaluation.metadata else None,
                        threshold=dict(evaluation.threshold) if evaluation.threshold else None,
                    )
                    for evaluation in evaluations
                ]
                event_json["properties"]["evaluations"] = formatted_eval_json
        except Exception:
            print("NEED TO LOG ERROR HERE")

        req = await global_state.http_client().post(
            url=INGESTION_ENDPOINT,
            json=event_json,
            headers=self._client_headers,
            timeout=self._timeout_seconds,
        )
        req.raise_for_status()
        resp = req.json()
        return SendEventResponse(trace_id=resp.get("traceId"))

    def send_event(
        self,
        message: str,
        # Require all arguments after message to be specified via key=value
        *,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None,
        evaluators: List[BaseEventEvaluator] = [],
        max_evaluator_concurrency: int = 5,
        prompt_tracking: Optional[Dict] = None,
    ) -> SendEventResponse:
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
            return future.result()
        except Exception as err:
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            if AutoblocksEnvVar.TRACER_THROW_ON_ERROR.get() == "1":
                raise err
            return SendEventResponse(trace_id=None)
