from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks.tracer import AutoblocksTracer
from tests.util import make_expected_body


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key")
    trace_id = ab.send_event("my-message")

    assert trace_id == "my-trace-id"


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key")
    trace_id = ab.send_event("my-message")

    assert trace_id is None


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key")
    ab.send_event("my-message", trace_id="my-trace-id")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )
    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.send_event("my-message", trace_id="override-trace-id")


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.set_trace_id("override-trace-id")
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(y=2),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.set_properties(dict(y=2))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1, y=2),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message")


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
                timestamp=None,
                properties=dict(x=1, y=2, z=3),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message", properties=dict(z=3))


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
                timestamp=None,
                properties=dict(x=3, y=2, z=3),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))
    ab.send_event("my-message", properties=dict(x=3, z=3))


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

    ab = AutoblocksTracer("mock-ingestion-key")
    ab.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")


def test_tracer_prod_catches_errors(httpx_mock):
    httpx_mock.add_exception(Exception())

    ab = AutoblocksTracer("mock-ingestion-key")
    trace_id = ab.send_event("my-message")
    assert trace_id is None


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
                timestamp=None,
                properties=dict(),
            )
        ),
    )

    ab = AutoblocksTracer("mock-ingestion-key")
    trace_id = ab.send_event("my-message")
    assert trace_id is None
