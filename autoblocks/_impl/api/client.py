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
from autoblocks._impl.api.models import Dataset
from autoblocks._impl.api.models import DatasetItem
from autoblocks._impl.api.models import DatasetWithItems
from autoblocks._impl.api.models import Event
from autoblocks._impl.api.models import RelativeTimeFilter
from autoblocks._impl.api.models import Trace
from autoblocks._impl.api.models import TraceFilter
from autoblocks._impl.api.models import TracesResponse
from autoblocks._impl.api.models import View
from autoblocks._impl.config.constants import API_ENDPOINT

log = logging.getLogger(__name__)


def make_trace_response(data: Dict) -> Trace:
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


def make_traces_response(data: Dict) -> TracesResponse:
    return TracesResponse(
        next_cursor=data.get("nextCursor"),
        traces=[make_trace_response(trace) for trace in data["traces"]],
    )


def snake_to_camel(s: str) -> str:
    return "".join(word.lower() if i == 0 else word.capitalize() for i, word in enumerate(s.split("_")))


def camel_case_factory(values: List[Tuple[str, Any]]) -> Dict:
    return dict(((snake_to_camel(k)), v) for k, v in values if v is not None)


class AutoblocksAPIClient:
    def __init__(self, api_key: str, timeout: timedelta = timedelta(seconds=10)) -> None:
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

    def get_trace(self, trace_id: str) -> Trace:
        req = self._client.get(f"/traces/{trace_id}")
        req.raise_for_status()
        return make_trace_response(req.json())

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

    def get_datasets(self) -> List[Dataset]:
        req = self._client.get("/datasets")
        req.raise_for_status()
        resp = req.json()
        return [Dataset(id=dataset["id"], name=dataset["name"]) for dataset in resp]

    def get_dataset(self, dataset_id: str) -> DatasetWithItems:
        req = self._client.get(f"/datasets/{dataset_id}")
        req.raise_for_status()
        resp = req.json()
        return DatasetWithItems(
            id=resp["id"],
            name=resp["name"],
            items=[DatasetItem(id=item["id"], input=item["input"], output=item["output"]) for item in resp["items"]],
        )
