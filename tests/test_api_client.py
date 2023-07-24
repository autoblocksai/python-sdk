import requests_mock

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import Event
from autoblocks.api.models import GetTracesFromViewResponse
from autoblocks.api.models import Trace
from autoblocks.api.models import View


def test_get_views():
    client = AutoblocksAPIClient("mock-api-key")

    with requests_mock.mock() as m:
        m.get(
            f"{API_ENDPOINT}/views",
            json={
                "views": [
                    {
                        "id": "view-id-1",
                        "name": "View 1",
                    },
                    {
                        "id": "view-id-2",
                        "name": "View 2",
                    },
                ]
            },
        )

        resp = client.get_views()

    assert resp.views == [
        View(id="view-id-1", name="View 1"),
        View(id="view-id-2", name="View 2"),
    ]

    assert m.call_count == 1

    call = m.request_history[0]
    assert call.method == "GET"
    assert call.url == f"{API_ENDPOINT}/views"
    assert call.headers["Authorization"] == "Bearer mock-api-key"


def test_get_traces_from_view():
    client = AutoblocksAPIClient("mock-api-key")

    with requests_mock.mock() as m:
        m.get(
            f"{API_ENDPOINT}/views/123/traces",
            json={
                "nextCursor": "abc",
                "traces": [
                    {
                        "id": "trace-1",
                        "events": [
                            {
                                "id": "event-1",
                                "traceId": "trace-1",
                                "message": "message-1",
                                "timestamp": "2021-01-01T00:00:00.000Z",
                                "properties": {"x": "1"},
                            },
                        ],
                    },
                    {
                        "id": "trace-2",
                        "events": [
                            {
                                "id": "event-2",
                                "traceId": "trace-2",
                                "message": "message-2",
                                "timestamp": "2021-01-01T00:00:00.000Z",
                                "properties": {"x": "2"},
                            }
                        ],
                    },
                ],
            },
        )

        traces = client.get_traces_from_view("123", page_size=10)

    assert traces == GetTracesFromViewResponse(
        next_cursor="abc",
        traces=[
            Trace(
                id="trace-1",
                events=[
                    Event(
                        id="event-1",
                        trace_id="trace-1",
                        message="message-1",
                        timestamp="2021-01-01T00:00:00.000Z",
                        properties={"x": "1"},
                    ),
                ],
            ),
            Trace(
                id="trace-2",
                events=[
                    Event(
                        id="event-2",
                        trace_id="trace-2",
                        message="message-2",
                        timestamp="2021-01-01T00:00:00.000Z",
                        properties={"x": "2"},
                    ),
                ],
            ),
        ],
    )

    assert m.call_count == 1

    call = m.request_history[0]
    assert call.method == "GET"
    assert call.url == f"{API_ENDPOINT}/views/123/traces?pageSize=10&nextCursor="
    assert call.headers["Authorization"] == "Bearer mock-api-key"
