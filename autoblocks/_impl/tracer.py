import asyncio
import contextvars
import dataclasses
import inspect
import logging
import uuid
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import TracerEvent
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled
from autoblocks._impl.util import get_running_loop
from autoblocks._impl.util import now_iso_8601

log = logging.getLogger(__name__)

evaluator_semaphore_registry: dict[str, asyncio.Semaphore] = {}  # evaluator_id -> semaphore


@dataclasses.dataclass(frozen=True)
class Payload:
    message: str
    trace_id: Optional[str]
    timestamp: str
    properties: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "traceId": self.trace_id,
            "timestamp": self.timestamp,
            "properties": self.properties,
        }


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
        self._throw_on_error = AutoblocksEnvVar.TRACER_THROW_ON_ERROR.get() == "1"

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

    @staticmethod
    def _evaluation_to_json(evaluation: Evaluation, evaluator_external_id: str) -> Dict[str, Any]:
        return dict(
            id=str(uuid.uuid4()),
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
            metadata=evaluation.metadata,
            evaluatorExternalId=evaluator_external_id,
        )

    @staticmethod
    async def _evaluate_event_unsafe(
        event: TracerEvent,
        evaluator: BaseEventEvaluator,
    ) -> Optional[Evaluation]:
        """
        This function is suffixed with _unsafe because it doesn't handle exceptions.
        Its caller will catch and handle all exceptions.
        """
        if evaluator.id not in evaluator_semaphore_registry:
            evaluator_semaphore_registry[evaluator.id] = asyncio.Semaphore(evaluator.max_concurrency)

        async with evaluator_semaphore_registry[evaluator.id]:
            if inspect.iscoroutinefunction(evaluator.evaluate_event):
                # mypy error:
                # error: Returning Any from function declared to return "Evaluation | None"  [no-any-return]
                # Not sure what mypy wants here, evaluate_event is typed correctly
                return await evaluator.evaluate_event(event)  # type: ignore
            else:
                ctx = contextvars.copy_context()
                return await global_state.event_loop().run_in_executor(
                    None,
                    ctx.run,  # type: ignore
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
        evaluators: Sequence[BaseEventEvaluator],
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

    async def _async_send_event(
        self,
        payload: Payload,
        evaluators: Optional[Sequence[BaseEventEvaluator]],
    ) -> None:
        # If there are evaluators, run them and compute the evaluations property
        if evaluators:
            try:
                evaluations = await self._run_evaluators_unsafe(
                    event=TracerEvent(
                        message=payload.message,
                        trace_id=payload.trace_id,
                        timestamp=payload.timestamp,
                        properties=payload.properties,
                    ),
                    evaluators=evaluators,
                )
                if evaluations:
                    # Update merged properties with computed evaluations property
                    payload = dataclasses.replace(
                        payload,
                        properties={
                            **payload.properties,
                            "evaluations": evaluations,
                        },
                    )
            except Exception as err:
                log.error("Unable to evaluate events. Error: %s", err, exc_info=True)

        try:
            if global_state.main_thread_has_finished():
                # If we're in a shutdown state, we need to use the sync client
                # to avoid scheduling new futures after the interpreter has shut down.
                # See https://github.com/boto/boto3/issues/3113
                log.debug("Sending event with SYNC client because interpreter has shut down")
                req = global_state.sync_http_client().post(
                    url=INGESTION_ENDPOINT,
                    json=payload.to_json(),
                    headers=self._client_headers,
                    timeout=self._timeout_seconds,
                )
            else:
                log.debug("Sending event with ASYNC client")
                req = await global_state.http_client().post(
                    url=INGESTION_ENDPOINT,
                    json=payload.to_json(),
                    headers=self._client_headers,
                    timeout=self._timeout_seconds,
                )
            req.raise_for_status()
        except Exception as err:
            # Since we don't call task.result() in the caller of this function,
            # we need to catch and log errors here in order for them to be
            # seen.
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            if self._throw_on_error:
                raise err

    def _sync_send_test_event_unsafe(
        self,
        payload: Payload,
    ) -> None:
        """Sends an event to the Autoblocks CLI in a testing environment."""
        if not self._cli_server_address:
            log.error("Failed to send test event to Autoblocks. CLI server address not set.")
            return
        test_case_run = test_case_run_context_var.get()
        if not test_case_run:
            log.error("Failed to send test event to Autoblocks. No test ID set.")
            return

        req = global_state.sync_http_client().post(
            url=f"{self._cli_server_address}/events",
            json=dict(
                testExternalId=test_case_run.test_id,
                testCaseHash=test_case_run.test_case_hash,
                event=payload.to_json(),
            ),
            timeout=self._timeout_seconds,
        )
        req.raise_for_status()

    def _make_request_payload(
        self,
        *,
        message: str,
        trace_id: Optional[str],
        timestamp: Optional[str],
        span_id: Optional[str],
        parent_span_id: Optional[str],
        properties: Optional[Dict[str, Any]],
        prompt_tracking: Optional[Dict[str, Any]],
    ) -> Payload:
        trace_id = trace_id or self._trace_id
        timestamp = timestamp or now_iso_8601()

        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})

        # Overwrite properties with any provided as top level arguments
        if span_id:
            merged_properties["span_id"] = span_id
        if parent_span_id:
            merged_properties["parent_span_id"] = parent_span_id
        if prompt_tracking:
            merged_properties["promptTracking"] = prompt_tracking

        return Payload(
            message=message,
            trace_id=trace_id,
            timestamp=timestamp,
            properties=merged_properties,
        )

    def _dispatch_event_unsafe(
        self,
        payload: Payload,
        evaluators: Optional[Sequence[BaseEventEvaluator]],
    ) -> None:
        task: AnyTask

        # Check if we're already in a running event loop
        if running_loop := get_running_loop():
            # If we are, execute the task on that loop
            task = running_loop.create_task(
                self._async_send_event(
                    payload=payload,
                    evaluators=evaluators,
                ),
            )
        else:
            # Otherwise, send the task to our background loop
            task = asyncio.run_coroutine_threadsafe(
                self._async_send_event(
                    payload=payload,
                    evaluators=evaluators,
                ),
                global_state.event_loop(),
            )

        # Add the task to the set of tasks the
        # global state will wait to complete
        # on shutdown
        global_state.add_background_task(task)

        if self._throw_on_error:
            # Wait for the result if AUTOBLOCKS_TRACER_THROW_ON_ERROR is set to true,
            # since we set this environment variable in end-to-end testing contexts
            # where we want to raise exceptions immediately.
            task.result()

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
        evaluators: Optional[Sequence[BaseEventEvaluator]] = None,
        prompt_tracking: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Sends an event to the Autoblocks ingestion API.
        """
        try:
            # Prepare request payload
            payload = self._make_request_payload(
                message=message,
                trace_id=trace_id,
                timestamp=timestamp,
                span_id=span_id,
                parent_span_id=parent_span_id,
                properties=properties,
                prompt_tracking=prompt_tracking,
            )

            # If the test case run contextvar is set, we are in a test context and should send events to the CLI.
            # We also do not run evaluators in a test context, so the only argument we pass here is `payload`.
            if test_case_run_context_var.get() is not None:
                self._sync_send_test_event_unsafe(payload)
                return

            # Otherwise we are in a real context and should send events to the Autoblocks ingestion API
            self._dispatch_event_unsafe(
                payload=payload,
                evaluators=evaluators,
            )
        except Exception as err:
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            if self._throw_on_error:
                raise err
