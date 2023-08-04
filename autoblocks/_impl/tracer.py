import logging
from datetime import timedelta
from typing import Dict
from typing import Optional

import httpx

from autoblocks._impl.config.constants import INGESTION_ENDPOINT

log = logging.getLogger(__name__)


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

    def send_event(
        self,
        message: str,
        # Require all arguments after message to be specified via key=value
        *,
        trace_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Sends an event to the Autoblocks ingestion API.

        Returns the event's traceId on success, otherwise None.
        """
        merged_properties = dict(self._properties)
        merged_properties.update(properties or {})

        trace_id = trace_id or self._trace_id

        try:
            req = self._client.post(
                url=INGESTION_ENDPOINT,
                json={
                    "message": message,
                    "traceId": trace_id,
                    "timestamp": timestamp,
                    "properties": merged_properties,
                },
            )
            req.raise_for_status()
            resp = req.json()
            return resp.get("traceId")
        except Exception as err:
            log.error(f"Failed to send event to Autoblocks: {err}", exc_info=True)
            return None
