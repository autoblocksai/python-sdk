import dataclasses
import os
import uuid
from datetime import datetime
from typing import Any
from typing import Optional
from unittest import mock

import freezegun
import pytest

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks.testing.models import BaseEvaluator
from autoblocks.testing.models import BaseEventEvaluator
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import Evaluation
from autoblocks.testing.models import Threshold
from autoblocks.testing.models import TracerEvent
from autoblocks.tracer import AutoblocksTracer
from autoblocks.tracer import flush
from tests.util import make_expected_body

mock_now = datetime(2021, 1, 1, 1, 1, 1, 1)
mock_now_timestamp = "2021-01-01T01:01:01.000001+00:00"


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(mock_now):
        yield


@pytest.fixture(autouse=True)
def reset_client():
    AutoblocksTracer._client = None  # type: ignore


def test_client_headers_init_with_key():
    tracer = AutoblocksTracer("mock-ingestion-key-as-argument")
    assert tracer._client_headers["Authorization"] == "Bearer mock-ingestion-key-as-argument"


@pytest.fixture(autouse=True)
def mock_env_vars():
    with mock.patch.dict(
        os.environ,
        {
            "AUTOBLOCKS_INGESTION_KEY": "mock-ingestion-key",
        },
    ):
        yield


def test_client_init_headers_with_env_var():
    tracer = AutoblocksTracer()
    assert tracer._client_headers["Authorization"] == "Bearer mock-ingestion-key"


def expect_ingestion_post_request(
    httpx_mock: Any,
    *,
    message: str,
    trace_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    status_code: int = 200,
) -> None:
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=status_code,
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(
            dict(
                message=message,
                traceId=trace_id,
                timestamp=timestamp or mock_now_timestamp,
                properties=properties or dict(),
            )
        ),
    )


def expect_cli_post_request(
    httpx_mock: Any,
    body: dict[str, Any],
) -> None:
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        method="POST",
        status_code=200,
        match_headers={"Authorization": "Bearer mock-ingestion-key"},
        match_content=make_expected_body(body),
    )


def test_tracer_send_event(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
    )
    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message")
    flush()


def test_tracer_with_trace_id_in_send_event(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="my-trace-id",
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", trace_id="my-trace-id")
    flush()


def test_tracer_with_trace_id_in_init(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="my-trace-id",
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message")
    flush()


def test_tracer_with_trace_id_override(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="override-trace-id",
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.send_event("my-message", trace_id="override-trace-id")
    flush()


def test_tracer_with_set_trace_id(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="override-trace-id",
    )

    tracer = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    tracer.set_trace_id("override-trace-id")
    tracer.send_event("my-message")
    flush()


def test_tracer_with_properties(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(x=1),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.send_event("my-message")
    flush()


def test_tracer_with_set_properties(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(y=2),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.set_properties(dict(y=2))
    tracer.send_event("my-message")
    flush()


def test_tracer_with_update_properties(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(x=1, y=2),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message")
    flush()


def test_tracer_with_update_properties_and_send_event_properties(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(x=1, y=2, z=3),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(z=3))
    flush()


def test_tracer_with_properties_with_conflicting_keys(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(x=3, y=2, z=3),
    )

    tracer = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    tracer.update_properties(dict(y=2))
    tracer.send_event("my-message", properties=dict(x=3, z=3))
    flush()


def test_tracer_with_timestamp(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        timestamp="2023-07-24T21:52:52.742Z",
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")
    flush()


def test_tracer_swallows_errors(httpx_mock):
    httpx_mock.add_exception(Exception())

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message")
    flush()


@mock.patch.dict(
    os.environ,
    dict(AUTOBLOCKS_TRACER_THROW_ON_ERROR="1"),
)
def test_tracer_throws_errors_when_configured(httpx_mock):
    class MyCustomException(Exception):
        pass

    httpx_mock.add_exception(MyCustomException())

    tracer = AutoblocksTracer("mock-ingestion-key")
    with pytest.raises(MyCustomException):
        tracer.send_event("my-message")


def test_tracer_handles_non_200(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        status_code=500,
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message")
    flush()


def test_tracer_sends_span_id_as_property(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(span_id="my-span-id"),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", span_id="my-span-id")
    flush()


def test_tracer_sends_parent_span_id_as_property(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(parent_span_id="my-parent-span-id"),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", parent_span_id="my-parent-span-id")
    flush()


def test_tracer_sends_span_id_and_parent_span_id_as_property(httpx_mock):
    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        properties=dict(span_id="my-span-id", parent_span_id="my-parent-span-id"),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event("my-message", span_id="my-span-id", parent_span_id="my-parent-span-id")
    flush()


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=["mock-uuid-1"],
)
def test_tracer_sends_evaluations(httpx_mock):
    tracer = AutoblocksTracer()

    class MyEvaluator(BaseEventEvaluator):
        id = "my-evaluator"

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            tracer.send_event(f"i am inside evaluator {self.id} with event {event.message}")
            return Evaluation(
                score=0.9,
                threshold=Threshold(gte=0.5),
            )

    expect_cli_post_request(
        httpx_mock,
        body=dict(
            message="my-message",
            traceId="my-trace-id",
            timestamp=mock_now_timestamp,
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
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        body=dict(
            message="i am inside evaluator my-evaluator with event my-message",
            timestamp=mock_now_timestamp,
            properties={},
        ),
    )

    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=mock_now_timestamp,
        properties={},
        evaluators=[MyEvaluator()],
    )

    flush()


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid={i}" for i in range(2)],
)
def test_tracer_sends_async_evaluations(httpx_mock):
    tracer = AutoblocksTracer()

    class MyEvaluator1(BaseEventEvaluator):
        id = "my-evaluator-1"

        async def evaluate_event(self, event: TracerEvent) -> Evaluation:
            tracer.send_event(f"i am inside evaluator {self.id} with event {event.message}")
            return Evaluation(
                score=0.9,
                threshold=Threshold(gte=0.5),
            )

    class MyEvaluator2(BaseEventEvaluator):
        id = "my-evaluator-2"

        async def evaluate_event(self, event: TracerEvent) -> Evaluation:
            tracer.send_event(f"i am inside evaluator {self.id} with event {event.message}")
            return Evaluation(
                score=0.3,
            )

    expect_cli_post_request(
        httpx_mock,
        body=dict(
            message="my-message",
            traceId="my-trace-id",
            timestamp=mock_now_timestamp,
            properties={
                "evaluations": [
                    {
                        "evaluatorExternalId": "my-evaluator-1",
                        "id": "mock-uuid-0",
                        "score": 0.9,
                        "metadata": None,
                        "threshold": {"lt": None, "lte": None, "gt": None, "gte": 0.5},
                    },
                    {
                        "evaluatorExternalId": "my-evaluator-2",
                        "id": "mock-uuid-1",
                        "score": 0.3,
                        "metadata": None,
                        "threshold": None,
                    },
                ]
            },
        ),
    )

    expect_cli_post_request(
        httpx_mock,
        body=dict(
            message="i am inside evaluator my-evaluator-1 with event my-message",
            timestamp=mock_now_timestamp,
            properties={},
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        body=dict(
            message="i am inside evaluator my-evaluator-2 with event my-message",
            timestamp=mock_now_timestamp,
            properties={},
        ),
    )

    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=mock_now_timestamp,
        properties={},
        evaluators=[MyEvaluator1(), MyEvaluator2()],
    )

    flush()


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid={i}" for i in range(2)],
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

    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="my-trace-id",
        properties={
            "evaluations": [
                {
                    "evaluatorExternalId": "my-valid-evaluator",
                    "id": "mock-uuid-0",
                    "score": 0.3,
                    "metadata": None,
                    "threshold": None,
                },
            ]
        },
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=mock_now_timestamp,
        properties={},
        evaluators=[MyFailingEvaluator(), MyValidEvaluator()],
    )

    flush()


@mock.patch.object(
    AutoblocksTracer,
    "_run_evaluators_unsafe",
    side_effect=Exception("Something went wrong with our code when evaluating the event"),
)
def test_tracer_evaluation_unexpected_error(httpx_mock):
    class MyEvaluator(BaseEventEvaluator):
        id = "my-evaluator"

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(score=1)

    expect_ingestion_post_request(
        httpx_mock,
        message="my-message",
        trace_id="my-trace-id",
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        "my-message",
        trace_id="my-trace-id",
        timestamp=mock_now_timestamp,
        properties={},
        evaluators=[MyEvaluator()],
    )

    flush()


@mock.patch.object(
    uuid,
    "uuid4",
    side_effect=[f"mock-uuid={i}" for i in range(1)],
)
def test_handles_evaluators_implementing_base_evaluator(httpx_mock):
    @dataclasses.dataclass
    class SomeTestCase(BaseTestCase):
        x: float

        def hash(self):
            return f"{self.x}"

    class MyCombinedEvaluator(BaseEvaluator):
        id = "my-combined-evaluator"

        @staticmethod
        def _some_shared_implementation(x: float) -> float:
            return x

        def evaluate_test_case(self, test_case: SomeTestCase, output: str) -> Evaluation:
            return Evaluation(
                score=self._some_shared_implementation(test_case.x),
            )

        def evaluate_event(self, event: TracerEvent) -> Evaluation:
            return Evaluation(
                score=self._some_shared_implementation(event.properties["x"]),
            )

    expect_ingestion_post_request(
        httpx_mock,
        message="this is a test",
        trace_id=None,
        properties=dict(
            x=0.5,
            evaluations=[
                dict(
                    id="mock-uuid-0",
                    score=0.5,
                    threshold=None,
                    metadata=None,
                    evaluatorExternalId="my-combined-evaluator",
                ),
            ],
        ),
    )

    tracer = AutoblocksTracer("mock-ingestion-key")
    tracer.send_event(
        message="this is a test",
        properties=dict(x=0.5),
        evaluators=[
            MyCombinedEvaluator(),
        ],
    )

    flush()
