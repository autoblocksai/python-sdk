import os
from unittest import mock

from httpx import Timeout

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import Event
from autoblocks.api.models import EventFilter
from autoblocks.api.models import EventFilterOperator
from autoblocks.api.models import RelativeTimeFilter
from autoblocks.api.models import Trace
from autoblocks.api.models import TraceFilter
from autoblocks.api.models import TraceFilterOperator
from autoblocks.api.models import TracesResponse
from autoblocks.api.models import View
from tests.util import make_expected_body


def test_client_init_with_key():
    client = AutoblocksAPIClient("mock-api-key")
    assert client._client.timeout == Timeout(10)
    assert client._client.headers.get("authorization") == "Bearer mock-api-key"


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_client_init_with_env_var():
    client = AutoblocksAPIClient()
    assert client._client.timeout == Timeout(10)
    assert client._client.headers.get("authorization") == "Bearer mock-api-key"


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

    assert traces == TracesResponse(
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


def test_search_traces(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/traces/search",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                pageSize=100,
                timeFilter=dict(
                    type="relative",
                    seconds=1,
                ),
                traceFilters=[
                    dict(
                        operator="CONTAINS",
                        eventFilters=[
                            dict(
                                key="key",
                                value="value",
                                operator="CONTAINS",
                            ),
                        ],
                    )
                ],
            ),
        ),
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
    traces = client.search_traces(
        page_size=100,
        time_filter=RelativeTimeFilter(
            seconds=1,
        ),
        trace_filters=[
            TraceFilter(
                operator=TraceFilterOperator.CONTAINS,
                event_filters=[
                    EventFilter(
                        key="key",
                        value="value",
                        operator=EventFilterOperator.CONTAINS,
                    ),
                ],
            ),
        ],
    )

    assert traces == TracesResponse(
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
