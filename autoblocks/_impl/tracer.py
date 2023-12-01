import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import Optional

import httpx

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.util import autoblocks_tracer_throw_on_error
from autoblocks._impl.util import make_replay_headers

log = logging.getLogger(__name__)


@dataclass
class SendEventResponse:
    trace_id: Optional[str]


class AutoblocksTracer:
    def __init__(
        self,
        ingestion_key: str,
        # Require all arguments after ingestion_key to be specified via key=value
        *,
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
        self._trace_id: Optional[str] = trace_id
        self._properties: Dict = properties or {}

        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {ingestion_key}"},
            timeout=timeout.total_seconds(),
        )

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

    def _send_event_unsafe(
        self,
        # Require all arguments to be specified via key=value
        *,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None,
    ) -> SendEventResponse:
        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})
        if span_id:
            merged_properties["span_id"] = span_id
        if parent_span_id:
            merged_properties["parent_span_id"] = parent_span_id

        trace_id = trace_id or self._trace_id
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        try:
            replay_headers = make_replay_headers()
        except Exception as err:
            log.error(f"Failed to generate replay headers: {err}", exc_info=True)
            replay_headers = None

        req = self._client.post(
            url=INGESTION_ENDPOINT,
            json={
                "message": message,
                "traceId": trace_id,
                "timestamp": timestamp,
                "properties": merged_properties,
            },
            headers=replay_headers,
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
    ) -> SendEventResponse:
        """
        Sends an event to the Autoblocks ingestion API.

        Always returns a SendEventResponse dataclass as the response. If sending
        the event failed, the trace_id will be None.
        """
        try:
            return self._send_event_unsafe(
                message=message,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                timestamp=timestamp,
                properties=properties,
            )
        except Exception as err:
            if autoblocks_tracer_throw_on_error():
                raise err

            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            return SendEventResponse(trace_id=None)
