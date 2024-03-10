import asyncio
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
from typing import Tuple
from typing import Union

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.context_vars import current_external_test_id
from autoblocks._impl.context_vars import current_test_case_hash
from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import TracerEvent
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled

log = logging.getLogger(__name__)

evaluator_semaphore_registry: dict[str, asyncio.Semaphore] = {}  # evaluator_id -> semaphore


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
        self._cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()

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

    async def _evaluate_event_unsafe(
        self,
        event: TracerEvent,
        evaluator: BaseEventEvaluator,
    ) -> Evaluation:
        """
        This function is suffixed with _unsafe because it doesn't handle exceptions.
        Its caller will catch and handle all exceptions.
        """
        if evaluator.id not in evaluator_semaphore_registry:
            evaluator_semaphore_registry[evaluator.id] = asyncio.Semaphore(evaluator.max_concurrency)

        async with evaluator_semaphore_registry[evaluator.id]:
            if inspect.iscoroutinefunction(evaluator.evaluate_event):
                # mypy error:
                # error: Returning Any from function declared to return "Evaluation"  [no-any-return]
                # Not sure what mypy wants here, evaluate_event is typed correctly
                return await evaluator.evaluate_event(event)  # type: ignore
            else:
                ctx = contextvars.copy_context()
                return await global_state.event_loop().run_in_executor(
                    None,
                    ctx.run,
                    evaluator.evaluate_event,
                    event,
                )

    async def _evaluate_event(self, event: TracerEvent, evaluator: BaseEventEvaluator) -> Optional[Evaluation]:
        """
        Evaluates an event using a provided evaluator.
        """
        try:
            return await self._evaluate_event_unsafe(
                event=event,
                evaluator=evaluator,
            )
        except Exception as err:
            log.error(f"Unable to execute evaluator with id: {evaluator.id}. Error: %s", err, exc_info=True)
            return None

    async def _run_evaluators_unsafe(
        self,
        event: TracerEvent,
        evaluators: List[BaseEventEvaluator],
    ) -> List[Dict[str, Any]]:
        """
        Run a list of evaluators on an event and return the evaluations as a list of dictionaries.

        This is suffixed with _unsafe because it doesn't handle exceptions.
        Its caller will catch and handle all exceptions.
        """
        if len(evaluators) == 0:
            return []
        evaluations: Tuple[Union[Optional[Evaluation], BaseException]] = await all_settled(
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
            if isinstance(evaluation, Evaluation)
        ]

    async def _send_event_unsafe(
        self,
        # Require all arguments to be specified via key=value
        *,
        message: str,
        timestamp: str,
        properties: Dict[Any, Any],
        trace_id: Optional[str],
        evaluators: Optional[List[BaseEventEvaluator]],
    ) -> None:
        # If there are evaluators, run them and compute the evaluations property
        if evaluators:
            try:
                evaluations = await self._run_evaluators_unsafe(
                    event=TracerEvent(
                        message=message,
                        trace_id=trace_id,
                        timestamp=timestamp,
                        properties=properties,
                    ),
                    evaluators=evaluators,
                )
                if evaluations:
                    # Update merged properties with computed evaluations property
                    properties["evaluations"] = evaluations
            except Exception as err:
                log.error("Unable to evaluate events. Error: %s", err, exc_info=True)

        traced_event = TracerEvent(
            message=message,
            trace_id=trace_id,
            timestamp=timestamp,
            properties=properties,
        )
        req = await global_state.http_client().post(
            url=INGESTION_ENDPOINT,
            json=traced_event.to_json(),
            headers=self._client_headers,
            timeout=self._timeout_seconds,
        )
        req.raise_for_status()

    def _send_test_event_unsafe(
        self,
        # Require all arguments to be specified via key=value
        *,
        message: str,
        timestamp: str,
        properties: Dict[Any, Any],
        trace_id: Optional[str],
    ) -> None:
        """Sends an event to the Autoblocks CLI in a testing environment."""
        if not self._cli_server_address:
            log.error("Failed to send test event to Autoblocks. CLI server address not set.")
            return

        if not current_external_test_id.get():
            log.error("Failed to send test event to Autoblocks. No test ID set.")
            return

        if not current_test_case_hash.get():
            log.error("Failed to send test event to Autoblocks. No test case hash set.")
            return

        traced_event = TracerEvent(
            message=message,
            trace_id=trace_id,
            timestamp=timestamp,
            properties=properties,
        )
        req = global_state.sync_http_client().post(
            url=f"{self._cli_server_address}/events",
            json=dict(
                testExternalId=current_external_test_id.get(),
                testCaseHash=current_test_case_hash.get(),
                event=traced_event.to_json(),
            ),
            timeout=self._timeout_seconds,
        )
        req.raise_for_status()

    def _merge_properties(
        self,
        *,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        prompt_tracking: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})

        # Overwrite properties with any provided as top level arguments
        if span_id:
            merged_properties["span_id"] = span_id
        if parent_span_id:
            merged_properties["parent_span_id"] = parent_span_id
        if prompt_tracking:
            merged_properties["promptTracking"] = prompt_tracking

        return merged_properties

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
        prompt_tracking: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Sends an event to the Autoblocks ingestion API.

        Always returns a SendEventResponse dataclass as the response. If sending
        the event failed, the trace_id will be None.
        """
        try:
            merged_properties = self._merge_properties(
                span_id=span_id, parent_span_id=parent_span_id, properties=properties, prompt_tracking=prompt_tracking
            )
            trace_id = trace_id or self._trace_id
            timestamp = timestamp or datetime.now(timezone.utc).isoformat()
            # If the CLI server address is set, we are in a test context and should send events to the CLI
            # We also do not run evaluators in a test context
            if self._cli_server_address:
                self._send_test_event_unsafe(
                    message=message,
                    trace_id=trace_id,
                    timestamp=timestamp,
                    properties=merged_properties,
                )
                return

            # Otherwise we are in a real context and should send events to the Autoblocks ingestion API
            future = asyncio.run_coroutine_threadsafe(
                self._send_event_unsafe(
                    message=message,
                    trace_id=trace_id,
                    timestamp=timestamp,
                    properties=merged_properties,
                    evaluators=evaluators,
                ),
                global_state.event_loop(),
            )
            future.result()  # Block on result: Todo: make this not blocking
        except Exception as err:
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            if AutoblocksEnvVar.TRACER_THROW_ON_ERROR.get() == "1":
                raise err
