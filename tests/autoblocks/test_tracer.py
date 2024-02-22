import os
import uuid
from datetime import datetime
from unittest import mock

import freezegun
import pytest
from httpx import Timeout

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks.tracer import AutoblocksTracer
from tests.autoblocks.util import make_expected_body


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(datetime(2021, 1, 1, 1, 1, 1, 1)):
        yield


@pytest.fixture(autouse=True)
def reset_client():
    AutoblocksTracer._client = None


timestamp = "2021-01-01T01:01:01.000001+00:00"


def test_client_init_with_key():
    tracer = AutoblocksTracer("mock-ingestion-key")
    assert tracer._client.timeout == Timeout(5)
    assert tracer._ingestion_key == "mock-ingestion-key"


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_INGESTION_KEY": "mock-ingestion-key",
    },
)
def test_client_init_with_env_var():
    tracer = AutoblocksTracer()
    assert tracer._client.timeout == Timeout(5)
    assert tracer._ingestion_key == "mock-ingestion-key"


def test_tracer_prod(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")

    assert resp.trace_id == "my-trace-id"


def test_tracer_prod_no_trace_id_in_response(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")

    assert resp.trace_id is None


def test_tracer_prod_with_trace_id_in_send_event(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", trace_id="my-trace-id")


def test_tracer_prod_with_trace_id_in_init(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message")


def test_tracer_prod_with_trace_id_override(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="override-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message", trace_id="override-trace-id")


def test_tracer_prod_with_set_trace_id(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="override-trace-id",
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.set_trace_id("override-trace-id")
    tracer.send_event("my-message")


def test_tracer_prod_with_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.send_event("my-message")


def test_tracer_prod_with_set_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(y=2),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.set_properties(dict(y=2))
    tracer.send_event("my-message")


def test_tracer_prod_with_update_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1, y=2),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message")


def test_tracer_prod_with_update_properties_and_send_event_properties(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=1, y=2, z=3),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(z=3))


def test_tracer_prod_with_properties_with_conflicting_keys(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(x=3, y=2, z=3),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(x=3, z=3))


def test_tracer_prod_with_timestamp(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp="2023-07-24T21:52:52.742Z",
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")


def test_tracer_prod_swallows_errors(httpx_mock):
    httpx_mock.add_exception(Exception())

    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")
    assert resp.trace_id is None


@mock.patch.dict(
    os.environ,
    dict(AUTOBLOCKS_TRACER_THROW_ON_ERROR="1"),
)
def test_tracer_prod_throws_errors_when_configured(httpx_mock):
    class MyCustomException(Exception):
        pass

    httpx_mock.add_exception(MyCustomException())

    tracer = AutoblocksTracer("mock-ingestion-key")
    with pytest.raises(MyCustomException):
        tracer.send_event("my-message")


def test_tracer_prod_handles_non_200(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=400,
        json={},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(),
            )
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message")
    assert resp.trace_id is None


def test_tracer_sends_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(span_id="my-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", span_id="my-span-id")

    assert resp.trace_id == "my-trace-id"


def test_tracer_sends_parent_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(parent_span_id="my-parent-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", parent_span_id="my-parent-span-id")

    assert resp.trace_id == "my-trace-id"


def test_tracer_sends_span_id_and_parent_span_id_as_property(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId=None,
                timestamp=timestamp,
                properties=dict(span_id="my-span-id", parent_span_id="my-parent-span-id"),
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    resp = tracer.send_event("my-message", span_id="my-span-id", parent_span_id="my-parent-span-id")

    assert resp.trace_id == "my-trace-id"


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_INGESTION_KEY": "key",
    },
)
@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid-{i}" for i in range(10)],
)
def test_tracer_start_span(*args, **kwargs):
    tracer = AutoblocksTracer()

    assert tracer._properties.get("span_id") is None
    assert tracer._properties.get("parent_span_id") is None

    with tracer.start_span():
        assert tracer._properties["span_id"] == "mock-uuid-0"
        assert tracer._properties.get("parent_span_id") is None

        with tracer.start_span():
            assert tracer._properties["span_id"] == "mock-uuid-1"
            assert tracer._properties["parent_span_id"] == "mock-uuid-0"

            with tracer.start_span():
                assert tracer._properties["span_id"] == "mock-uuid-2"
                assert tracer._properties["parent_span_id"] == "mock-uuid-1"

        with tracer.start_span():
            assert tracer._properties["span_id"] == "mock-uuid-3"
            assert tracer._properties["parent_span_id"] == "mock-uuid-0"

        assert tracer._properties["span_id"] == "mock-uuid-0"
        assert tracer._properties.get("parent_span_id") is None

    assert tracer._properties.get("span_id") is None
    assert tracer._properties.get("parent_span_id") is None


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_INGESTION_KEY": "key",
    },
)
def test_tracer_single_client():
    tracer1 = AutoblocksTracer()
    assert tracer1._client is not None
    tracer2 = AutoblocksTracer()
    assert tracer2._client is tracer1._client
    assert id(tracer2._client) == id(tracer1._client)
