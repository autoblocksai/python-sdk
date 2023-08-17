from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import Event
from autoblocks.api.models import GetTracesFromViewResponse
from autoblocks.api.models import Trace
from autoblocks.api.models import View


def test_get_views(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/views",
        method="GET",
        status_code=200,
        json=[
            {
                "id": "view-id-1",
                "name": "View 1",
            },
            {
                "id": "view-id-2",
                "name": "View 2",
            },
        ],
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    views = client.get_views()

    assert views == [
        View(id="view-id-1", name="View 1"),
        View(id="view-id-2", name="View 2"),
    ]


def test_get_traces_from_view(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/views/123/traces?pageSize=10&cursor=",
        method="GET",
        status_code=200,
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
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
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
