import os
import uuid
from datetime import datetime
from unittest import mock

import freezegun
import pytest

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.testing.models import BaseEventEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.models import TracerEvent
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


def test_client_headers_init_with_key():
    tracer = AutoblocksTracer("mock-ingestion-key")
    assert tracer._client_headers["Authorization"] == "Bearer mock-ingestion-key"


@pytest.fixture(autouse=True)
def mock_evn_vars():
    with mock.patch.dict(
        os.environ,
        {
            "AUTOBLOCKS_INGESTION_KEY": "mock-ingestion-key",
            "TRACER_BLOCK_ON_SEND_EVENT": "1",
        },
    ):
        yield


def test_client_init_headers_with_env_var():
    tracer = AutoblocksTracer()
    assert tracer._client_headers["Authorization"] == "Bearer mock-ingestion-key"


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
    tracer.send_event("my-message")


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
    tracer.send_event("my-message")


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
    tracer.send_event("my-message")


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
    tracer.send_event("my-message")


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
    tracer.send_event("my-message", span_id="my-span-id")


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
    tracer.send_event("my-message", parent_span_id="my-parent-span-id")


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
    tracer.send_event("my-message", span_id="my-span-id", parent_span_id="my-parent-span-id")


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid-{i}" for i in range(4)],
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


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=["mock-uuid-1"],
)
def test_tracer_prod_evaluations(httpx_mock):
    class MyEvaluator(BaseEventEvaluator):
        id = "my-evaluator"

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(
                score=0.9,
                threshold=Threshold(gte=0.5),
            )

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties={
                    "evaluations": [
                        {
                            "id": "mock-uuid-1",
                            "score": 0.9,
                            "metadata": None,
                            "threshold": {"lt": None, "lte": None, "gt": None, "gte": 0.5},
                            "evaluatorExternalId": "my-evaluator",
                        }
                    ]
                },
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=timestamp,
        properties={},
        evaluators=[MyEvaluator()],
    )


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=["mock-uuid" for _ in range(2)],
)
def test_tracer_prod_async_evaluations(httpx_mock):
    class MyEvaluator1(BaseEventEvaluator):
        id = "my-evaluator-1"

        async def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(
                score=0.9,
                threshold=Threshold(gte=0.5),
            )

    class MyEvaluator2(BaseEventEvaluator):
        id = "my-evaluator-2"

        async def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(
                score=0.3,
            )

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties={
                    "evaluations": [
                        {
                            "evaluatorExternalId": "my-evaluator-1",
                            "id": "mock-uuid",
                            "score": 0.9,
                            "metadata": None,
                            "threshold": {"lt": None, "lte": None, "gt": None, "gte": 0.5},
                        },
                        {
                            "evaluatorExternalId": "my-evaluator-2",
                            "id": "mock-uuid",
                            "score": 0.3,
                            "metadata": None,
                            "threshold": None,
                        },
                    ]
                },
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=timestamp,
        properties={},
        evaluators=[MyEvaluator1(), MyEvaluator2()],
    )


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=["mock-uuid" for i in range(2)],
)
def test_tracer_failing_evaluation(httpx_mock):
    class MyValidEvaluator(BaseEventEvaluator):
        id = "my-valid-evaluator"

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(
                score=0.3,
            )

    class MyFailingEvaluator(BaseEventEvaluator):
        id = "my-failing-evaluator"

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            raise Exception("Something terrible went wrong")

    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        json={"traceId": "my-trace-id"},
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message="my-message",
                traceId="my-trace-id",
                timestamp=timestamp,
                properties={
                    "evaluations": [
                        {
                            "evaluatorExternalId": "my-valid-evaluator",
                            "id": "mock-uuid",
                            "score": 0.3,
                            "metadata": None,
                            "threshold": None,
                        },
                    ]
                },
            )
        ),
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=timestamp,
        properties={},
        evaluators=[MyFailingEvaluator(), MyValidEvaluator()],
    )
