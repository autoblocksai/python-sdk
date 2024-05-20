import logging
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import httpx

from autoblocks._impl.api.models import AbsoluteTimeFilter
from autoblocks._impl.api.models import Event
from autoblocks._impl.api.models import ManagedTestCase
from autoblocks._impl.api.models import ManagedTestCaseResponse
from autoblocks._impl.api.models import RelativeTimeFilter
from autoblocks._impl.api.models import Trace
from autoblocks._impl.api.models import TraceFilter
from autoblocks._impl.api.models import TracesResponse
from autoblocks._impl.api.models import View
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.util import AutoblocksEnvVar

log = logging.getLogger(__name__)


def make_trace_response(data: Dict[str, Any]) -> Trace:
    return Trace(
        id=data["id"],
        events=[
            Event(
                id=event["id"],
                trace_id=event["traceId"],
                message=event["message"],
                timestamp=event["timestamp"],
                properties=event.get("properties") or {},
            )
            for event in data["events"]
        ],
    )


def make_traces_response(data: Dict[str, Any]) -> TracesResponse:
    return TracesResponse(
        next_cursor=data.get("nextCursor"),
        traces=[make_trace_response(trace) for trace in data["traces"]],
    )


def snake_to_camel(s: str) -> str:
    return "".join(word.lower() if i == 0 else word.capitalize() for i, word in enumerate(s.split("_")))


def camel_case_factory(values: List[Tuple[str, Any]]) -> Dict[str, Any]:
    return dict(((snake_to_camel(k)), v) for k, v in values if v is not None)


class AutoblocksAPIClient:
    def __init__(self, api_key: Optional[str] = None, timeout: timedelta = timedelta(seconds=10)) -> None:
        api_key = api_key or AutoblocksEnvVar.API_KEY.get()
        if not api_key:
            raise ValueError(f"You must provide an api_key or set the {AutoblocksEnvVar.API_KEY} environment variable.")
        self._client = httpx.Client(
            base_url=API_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout.total_seconds(),
        )

    def get_views(self) -> List[View]:
        req = self._client.get("/views")
        req.raise_for_status()
        resp = req.json()
        return [View(id=view["id"], name=view["name"]) for view in resp]

    def get_traces_from_view(self, view_id: str, *, page_size: int, cursor: Optional[str] = None) -> TracesResponse:
        req = self._client.get(
            f"/views/{view_id}/traces",
            params={"pageSize": page_size, "cursor": cursor or ""},
        )
        req.raise_for_status()
        return make_traces_response(req.json())

    def search_traces(
        self,
        *,
        page_size: int,
        time_filter: Union[RelativeTimeFilter, AbsoluteTimeFilter],
        trace_filters: Optional[List[TraceFilter]] = None,
        query: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> TracesResponse:
        payload = dict(
            pageSize=page_size,
            timeFilter=asdict(time_filter, dict_factory=camel_case_factory) if time_filter else None,
            traceFilters=[asdict(f, dict_factory=camel_case_factory) for f in trace_filters] if trace_filters else None,
            query=query,
            cursor=cursor,
        )
        payload = {k: v for k, v in payload.items() if v is not None}
        req = self._client.post(
            "/traces/search",
            json=payload,
        )
        req.raise_for_status()
        return make_traces_response(req.json())

    def get_test_cases(self, test_suite_id: str) -> ManagedTestCaseResponse:
        req = self._client.get(f"/test-suites/{test_suite_id}/test-cases")
        req.raise_for_status()
        resp = req.json()
        return ManagedTestCaseResponse(
            test_cases=[ManagedTestCase(id=case["id"], body=case["body"]) for case in resp["testCases"]]
        )
