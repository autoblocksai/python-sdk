import logging
from typing import Optional

import httpx

from autoblocks._impl.api.models import Event
from autoblocks._impl.api.models import GetTracesFromViewResponse
from autoblocks._impl.api.models import GetViewsResponse
from autoblocks._impl.api.models import Trace
from autoblocks._impl.api.models import View
from autoblocks._impl.config.constants import API_ENDPOINT

log = logging.getLogger(__name__)


class AutoblocksAPIClient:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.Client(
            base_url=API_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def get_views(self) -> GetViewsResponse:
        req = self._client.get("/views")
        req.raise_for_status()
        resp = req.json()
        return GetViewsResponse(views=[View(id=view["id"], name=view["name"]) for view in resp["views"]])

    def get_traces_from_view(
        self, view_id: str, *, page_size: int, cursor: Optional[str] = None
    ) -> GetTracesFromViewResponse:
        req = self._client.get(
            f"/views/{view_id}/traces",
            params={"pageSize": page_size, "cursor": cursor or ""},
        )
        req.raise_for_status()
        resp = req.json()
        return GetTracesFromViewResponse(
            next_cursor=resp.get("nextCursor"),
            traces=[
                Trace(
                    id=trace["id"],
                    events=[
                        Event(
                            id=event["id"],
                            trace_id=trace["id"],
                            message=event["message"],
                            timestamp=event["timestamp"],
                            properties=event.get("properties") or {},
                        )
                        for event in trace["events"]
                    ],
                )
                for trace in resp["traces"]
            ],
        )
