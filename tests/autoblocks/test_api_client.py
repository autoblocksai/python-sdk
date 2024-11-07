import os
from unittest import mock

from httpx import Timeout

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import AutoblocksTestCaseResult
from autoblocks.api.models import AutoblocksTestCaseResultId
from autoblocks.api.models import AutoblocksTestCaseResultPair
from autoblocks.api.models import AutoblocksTestCaseResultPairId
from autoblocks.api.models import AutoblocksTestCaseResultWithEvaluations
from autoblocks.api.models import AutoblocksTestRun
from autoblocks.api.models import EvaluationAssertion
from autoblocks.api.models import EvaluationWithEvaluatorId
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


def test_get_test_cases(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/test-suites/suite-id/test-cases",
        method="GET",
        status_code=200,
        json={"testCases": [{"id": "some_id", "body": {"input": "test"}}]},
    )

    client = AutoblocksAPIClient("mock-api-key")
    test_case_response = client.get_test_cases("suite-id")

    assert len(test_case_response.test_cases) == 1


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


def test_get_local_test_runs(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/local/tests/test-external-id/runs",
        method="GET",
        status_code=200,
        json={
            "runs": [
                {"id": "run-1"},
                {"id": "run-2"},
            ],
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    runs = client.get_local_test_runs("test-external-id")

    assert len(runs) == 2
    assert all(isinstance(run, AutoblocksTestRun) for run in runs)
    assert [run.id for run in runs] == ["run-1", "run-2"]


def test_get_ci_test_runs(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/ci/tests/test-external-id/runs",
        method="GET",
        status_code=200,
        json={
            "runs": [
                {"id": "ci-run-1"},
                {"id": "ci-run-2"},
            ],
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    runs = client.get_ci_test_runs("test-external-id")

    assert len(runs) == 2
    assert all(isinstance(run, AutoblocksTestRun) for run in runs)
    assert [run.id for run in runs] == ["ci-run-1", "ci-run-2"]


def test_get_local_test_results(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/local/runs/run-id/results",
        method="GET",
        status_code=200,
        json={
            "results": [
                {"id": "result-1"},
                {"id": "result-2"},
            ],
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    results = client.get_local_test_results("run-id")

    assert len(results) == 2
    assert all(isinstance(result, AutoblocksTestCaseResultId) for result in results)
    assert [result.id for result in results] == ["result-1", "result-2"]


def test_get_ci_test_results(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/ci/runs/run-id/results",
        method="GET",
        status_code=200,
        json={
            "results": [
                {"id": "ci-result-1"},
                {"id": "ci-result-2"},
            ],
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    results = client.get_ci_test_results("run-id")

    assert len(results) == 2
    assert all(isinstance(result, AutoblocksTestCaseResultId) for result in results)
    assert [result.id for result in results] == ["ci-result-1", "ci-result-2"]


def test_get_local_test_result(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/local/results/local-result-id",
        method="GET",
        status_code=200,
        json={
            "testCaseResult": {
                "id": "local-result-id",
                "runId": "local-run-id",
                "hash": "local-hash-value",
                "datasetItemId": "local-dataset-item-id",
                "durationMs": 150,
                "events": [
                    {
                        "id": "some_id",
                        "traceId": "some_trace_id",
                        "message": "local-event",
                        "timestamp": "some_timestamp",
                        "properties": {},
                    }
                ],
                "body": {"input": "local test input"},
                "output": {"result": "local test output"},
                "evaluations": [
                    {
                        "evaluatorId": "local-evaluator-1",
                        "score": 0.95,
                        "passed": True,
                        "metadata": {"key": "local-value"},
                        "assertions": [
                            {
                                "passed": True,
                                "required": True,
                                "criterion": "criterion-1",
                            }
                        ],
                    }
                ],
            }
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    result = client.get_local_test_result("local-result-id")

    assert isinstance(result, AutoblocksTestCaseResultWithEvaluations)
    assert result == AutoblocksTestCaseResultWithEvaluations(
        id="local-result-id",
        run_id="local-run-id",
        hash="local-hash-value",
        dataset_item_id="local-dataset-item-id",
        duration_ms=150,
        events=[
            Event(
                id="some_id",
                trace_id="some_trace_id",
                message="local-event",
                timestamp="some_timestamp",
                properties={},
            ),
        ],
        body={"input": "local test input"},
        output={"result": "local test output"},
        evaluations=[
            EvaluationWithEvaluatorId(
                evaluator_id="local-evaluator-1",
                score=0.95,
                passed=True,
                metadata={"key": "local-value"},
                assertions=[
                    EvaluationAssertion(
                        passed=True,
                        required=True,
                        criterion="criterion-1",
                        metadata=None,
                    )
                ],
            )
        ],
    )


def test_get_ci_test_result(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/testing/ci/results/ci-result-id",
        method="GET",
        status_code=200,
        json={
            "testCaseResult": {
                "id": "ci-result-id",
                "runId": "ci-run-id",
                "hash": "ci-hash-value",
                "datasetItemId": "ci-dataset-item-id",
                "durationMs": 200,
                "events": [
                    {
                        "id": "some_id",
                        "traceId": "some_trace_id",
                        "message": "ci-event",
                        "timestamp": "some_timestamp",
                        "properties": {},
                    }
                ],
                "body": {"input": "ci test input"},
                "output": {"result": "ci test output"},
                "evaluations": [
                    {
                        "evaluatorId": "ci-evaluator-1",
                        "score": 0.85,
                        "passed": True,
                        "metadata": {"key": "ci-value"},
                        "assertions": [
                            {
                                "passed": True,
                                "required": True,
                                "criterion": "criterion-1",
                            }
                        ],
                    }
                ],
            }
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    result = client.get_ci_test_result("ci-result-id")

    assert isinstance(result, AutoblocksTestCaseResultWithEvaluations)
    assert result == AutoblocksTestCaseResultWithEvaluations(
        id="ci-result-id",
        run_id="ci-run-id",
        hash="ci-hash-value",
        dataset_item_id="ci-dataset-item-id",
        duration_ms=200,
        events=[
            Event(
                id="some_id",
                trace_id="some_trace_id",
                message="ci-event",
                timestamp="some_timestamp",
                properties={},
            ),
        ],
        body={"input": "ci test input"},
        output={"result": "ci test output"},
        evaluations=[
            EvaluationWithEvaluatorId(
                evaluator_id="ci-evaluator-1",
                score=0.85,
                passed=True,
                metadata={"key": "ci-value"},
                threshold=None,
                assertions=[
                    EvaluationAssertion(
                        passed=True,
                        required=True,
                        criterion="criterion-1",
                        metadata=None,
                    )
                ],
            )
        ],
    )


def test_get_human_review_job_pairs(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/human-review/jobs/job-123/pairs",
        method="GET",
        status_code=200,
        json={
            "pairs": [
                {"id": "pair-1"},
                {"id": "pair-2"},
            ],
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    pairs = client.get_human_review_job_pairs("job-123")

    assert len(pairs) == 2
    assert all(isinstance(pair, AutoblocksTestCaseResultPairId) for pair in pairs)
    assert [pair.id for pair in pairs] == ["pair-1", "pair-2"]


def test_get_human_review_job_pair(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/human-review/jobs/job-123/pairs/pair-456",
        method="GET",
        status_code=200,
        json={
            "pair": {
                "id": "pair-456",
                "hash": "hash-value",
                "chosenOutputId": "result-1",
                "testCaseResults": [
                    {
                        "id": "result-1",
                        "runId": "run-1",
                        "hash": "hash-1",
                        "datasetItemId": "dataset-1",
                        "durationMs": 100,
                        "events": [
                            {
                                "id": "event-1",
                                "traceId": "trace-1",
                                "message": "test event 1",
                                "timestamp": "2024-03-20T10:00:00Z",
                                "properties": {"key": "value"},
                            }
                        ],
                        "body": {"input": "test input 1"},
                        "output": {"result": "test output 1"},
                    },
                    {
                        "id": "result-2",
                        "runId": "run-2",
                        "hash": "hash-2",
                        "datasetItemId": "dataset-2",
                        "durationMs": 150,
                        "events": [
                            {
                                "id": "event-2",
                                "traceId": "trace-2",
                                "message": "test event 2",
                                "timestamp": "2024-03-20T10:01:00Z",
                                "properties": {"key": "value"},
                            }
                        ],
                        "body": {"input": "test input 2"},
                        "output": {"result": "test output 2"},
                    },
                ],
            }
        },
        match_headers={"Authorization": "Bearer mock-api-key"},
    )

    client = AutoblocksAPIClient("mock-api-key")
    pair = client.get_human_review_job_pair("job-123", "pair-456")

    assert isinstance(pair, AutoblocksTestCaseResultPair)
    assert pair == AutoblocksTestCaseResultPair(
        id="pair-456",
        hash="hash-value",
        chosen_output_id="result-1",
        test_case_results=[
            AutoblocksTestCaseResult(
                id="result-1",
                run_id="run-1",
                hash="hash-1",
                dataset_item_id="dataset-1",
                duration_ms=100,
                events=[
                    Event(
                        id="event-1",
                        trace_id="trace-1",
                        message="test event 1",
                        timestamp="2024-03-20T10:00:00Z",
                        properties={"key": "value"},
                    )
                ],
                body={"input": "test input 1"},
                output={"result": "test output 1"},
            ),
            AutoblocksTestCaseResult(
                id="result-2",
                run_id="run-2",
                hash="hash-2",
                dataset_item_id="dataset-2",
                duration_ms=150,
                events=[
                    Event(
                        id="event-2",
                        trace_id="trace-2",
                        message="test event 2",
                        timestamp="2024-03-20T10:01:00Z",
                        properties={"key": "value"},
                    )
                ],
                body={"input": "test input 2"},
                output={"result": "test output 2"},
            ),
        ],
    )
