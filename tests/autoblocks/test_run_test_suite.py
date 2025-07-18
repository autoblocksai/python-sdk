import abc
import asyncio
import dataclasses
import datetime
import json
import os
import uuid
from typing import Optional
from typing import Union
from unittest import mock

import httpx
import pydantic
import pytest

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.context import PromptExecutionContext
from autoblocks._impl.prompts.manager import AutoblocksPromptManager
from autoblocks._impl.prompts.renderer import TemplateRenderer
from autoblocks._impl.prompts.renderer import ToolRenderer
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import StrEnum
from autoblocks.testing.models import BaseEvaluator
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import CreateHumanReviewJob
from autoblocks.testing.models import Evaluation
from autoblocks.testing.models import HumanReviewField
from autoblocks.testing.models import HumanReviewFieldContentType
from autoblocks.testing.models import TestCaseConfig
from autoblocks.testing.models import Threshold
from autoblocks.testing.models import TracerEvent
from autoblocks.testing.run import grid_search_ctx
from autoblocks.testing.run import run_test_suite
from autoblocks.testing.util import md5
from autoblocks.tracer import AutoblocksTracer
from tests.util import ANY_NUMBER
from tests.util import ANY_STRING
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import decode_request_body
from tests.util import expect_api_post_request
from tests.util import expect_cli_post_request


@pytest.fixture(autouse=True)
def mock_cli_server_address_env_var():
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.CLI_SERVER_ADDRESS.value: MOCK_CLI_SERVER_ADDRESS,
        },
    ):
        yield


@dataclasses.dataclass
class MyTestCase(BaseTestCase):
    input: str

    def hash(self) -> str:
        return self.input


def test_no_test_cases(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[],
        fn=lambda _: None,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == "/errors"
    req_body = decode_request_body(req)
    assert req_body["testExternalId"] == "my-test-id"
    assert req_body["testCaseHash"] is None
    assert req_body["evaluatorExternalId"] is None
    assert req_body["error"]["name"] == "AssertionError"
    assert req_body["error"]["message"] == "[my-test-id] No test cases provided."
    assert "AssertionError: [my-test-id] No test cases provided." in req_body["error"]["stacktrace"]


def test_invalid_test_cases(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[1, 2, 3],  # type: ignore
        evaluators=[],
        fn=lambda _: None,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == "/errors"
    req_body = decode_request_body(req)
    assert req_body["testExternalId"] == "my-test-id"
    assert req_body["testCaseHash"] is None
    assert req_body["evaluatorExternalId"] is None
    assert req_body["error"]["name"] == "AssertionError"
    assert req_body["error"]["message"] == "[my-test-id] Test case 1 does not implement BaseTestCase."
    assert (
        "AssertionError: [my-test-id] Test case 1 does not implement BaseTestCase." in req_body["error"]["stacktrace"]
    )


def test_duplicate_test_case_hashes(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[MyTestCase(input="a"), MyTestCase(input="a")],
        evaluators=[],
        fn=lambda _: None,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == "/errors"
    req_body = decode_request_body(req)
    assert req_body["testExternalId"] == "my-test-id"
    assert req_body["testCaseHash"] is None
    assert req_body["evaluatorExternalId"] is None
    assert req_body["error"]["name"] == "AssertionError"
    assert (
        req_body["error"]["message"]
        == "[my-test-id] Duplicate test case hash: 'a'. See https://docs.autoblocks.ai/testing/sdk-reference#test-case-hashing"
    )
    assert (
        "AssertionError: [my-test-id] Duplicate test case hash: 'a'. See https://docs.autoblocks.ai/testing/sdk-reference#test-case-hashing"
        in req_body["error"]["stacktrace"]
    )


def test_invalid_evaluators(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[1, 2, 3],  # type: ignore
        fn=lambda _: None,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == "/errors"
    req_body = decode_request_body(req)
    assert req_body["testExternalId"] == "my-test-id"
    assert req_body["testCaseHash"] is None
    assert req_body["evaluatorExternalId"] is None
    assert req_body["error"]["name"] == "AssertionError"
    assert req_body["error"]["message"] == "[my-test-id] Evaluator 1 does not implement BaseTestEvaluator."
    assert (
        "AssertionError: [my-test-id] Evaluator 1 does not implement BaseTestEvaluator."
        in req_body["error"]["stacktrace"]
    )


def test_duplicate_evaluator_ids(httpx_mock):
    httpx_mock.add_response()

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> None:
            return None

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[MyEvaluator(), MyEvaluator()],
        fn=lambda _: None,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == "/errors"
    req_body = decode_request_body(req)
    assert req_body["testExternalId"] == "my-test-id"
    assert req_body["testCaseHash"] is None
    assert req_body["evaluatorExternalId"] is None
    assert req_body["error"]["name"] == "AssertionError"
    assert (
        req_body["error"]["message"]
        == "[my-test-id] Duplicate evaluator id: 'my-evaluator'. Each evaluator id must be unique."
    )
    assert (
        "AssertionError: [my-test-id] Duplicate evaluator id: 'my-evaluator'. Each evaluator id must be unique."
        in req_body["error"]["stacktrace"]
    )


def test_error_in_test_fn(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
        body=None,
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        if test_case.input == "a":
            return test_case.input + "!"
        raise ValueError(test_case.input + "!")

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["testExternalId"] == "my-test-id"
    assert error_req_body["runId"] == mock_run_id
    assert error_req_body["testCaseHash"] == "b"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_body["error"]["stacktrace"]


def test_error_in_async_test_fn(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
        body=None,
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    async def test_fn(test_case: MyTestCase) -> str:
        if test_case.input == "a":
            return test_case.input + "!"
        raise ValueError(test_case.input + "!")

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["testExternalId"] == "my-test-id"
    assert error_req_body["runId"] == mock_run_id
    assert error_req_body["testCaseHash"] == "b"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_body["error"]["stacktrace"]


def test_error_in_evaluator(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="my-sync-evaluator",
            score=0.5,
            threshold=dict(lt=0.6, lte=None, gt=None, gte=None),
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="my-async-evaluator",
            score=0.6,
            threshold=dict(lt=0.7, lte=None, gt=None, gte=None),
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
        body=None,
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    class MySyncEvaluator(BaseTestEvaluator):
        id = "my-sync-evaluator"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            if test_case.input == "a":
                return Evaluation(
                    score=0.5,
                    threshold=Threshold(lt=0.6),
                )
            raise ValueError(output)

    class MyAsyncEvaluator(BaseTestEvaluator):
        id = "my-async-evaluator"

        async def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            if test_case.input == "b":
                return Evaluation(
                    score=0.6,
                    threshold=Threshold(lt=0.7),
                )
            raise ValueError(output)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[MySyncEvaluator(), MyAsyncEvaluator()],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    error_reqs = [r for r in requests if r.url.path == "/errors"]
    assert len(error_reqs) == 2
    error_req_bodies = [decode_request_body(r) for r in error_reqs]
    error_req_sync = [e for e in error_req_bodies if e["evaluatorExternalId"] == MySyncEvaluator.id][0]
    error_req_async = [e for e in error_req_bodies if e["evaluatorExternalId"] == MyAsyncEvaluator.id][0]

    assert error_req_sync["testExternalId"] == "my-test-id"
    assert error_req_sync["runId"] == mock_run_id
    assert error_req_sync["testCaseHash"] == "b"
    assert error_req_sync["evaluatorExternalId"] == "my-sync-evaluator"
    assert error_req_sync["error"]["name"] == "ValueError"
    assert error_req_sync["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_sync["error"]["stacktrace"]

    assert error_req_async["testExternalId"] == "my-test-id"
    assert error_req_async["runId"] == mock_run_id
    assert error_req_async["testCaseHash"] == "a"
    assert error_req_async["evaluatorExternalId"] == "my-async-evaluator"
    assert error_req_async["error"]["name"] == "ValueError"
    assert error_req_async["error"]["message"] == "a!"
    assert "ValueError: a!" in error_req_async["error"]["stacktrace"]


def test_no_evaluators(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_with_evaluators(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-a",
            score=0,
            threshold=None,
            metadata=dict(reason="because"),
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-b",
            score=1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="evaluator-a",
            score=0,
            threshold=None,
            metadata=dict(reason="because"),
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="evaluator-b",
            score=1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    class EvaluatorA(BaseTestEvaluator):
        id = "evaluator-a"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0, metadata=dict(reason="because"))

    class EvaluatorB(BaseTestEvaluator):
        id = "evaluator-b"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=1)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[
            EvaluatorA(),
            EvaluatorB(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_concurrency(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    httpx_mock.add_response()

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    class EvaluatorA(BaseTestEvaluator):
        id = "evaluator-a"
        max_concurrency = 1

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0)

    class EvaluatorB(BaseTestEvaluator):
        id = "evaluator-b"
        max_concurrency = 1

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=1)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[
            EvaluatorA(),
            EvaluatorB(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    # The requests should be in a deterministic order when the concurrency is set to 1
    requests = [(req.url.path, decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        (
            "/start",
            dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        (
            "/results",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        (
            "/results",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
                revisionUsage=None,
                assertions=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
                revisionUsage=None,
                assertions=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="b",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
                revisionUsage=None,
                assertions=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="b",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
                revisionUsage=None,
                assertions=None,
            ),
        ),
        (
            "/end",
            dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


def test_async_test_fn(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    async def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_async_evaluators(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-a",
            score=0,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-b",
            score=1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="evaluator-a",
            score=0,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="evaluator-b",
            score=1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    class EvaluatorA(BaseTestEvaluator):
        id = "evaluator-a"

        async def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0)

    class EvaluatorB(BaseTestEvaluator):
        id = "evaluator-b"

        async def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=1)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[
            EvaluatorA(),
            EvaluatorB(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "CI": "false",
    },
)
def test_creates_human_review_job(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )
    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/human-review-job",
        body=dict(
            assigneeEmailAddress="test@test.com",
            name="test",
        ),
    )

    async def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        human_review_job=CreateHumanReviewJob(
            assignee_email_address="test@test.com",
            name="test",
        ),
    )


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "CI": "false",
    },
)
def test_creates_human_review_jobs(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )
    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/human-review-job",
        body=dict(
            assigneeEmailAddress="test@test.com",
            name="test",
        ),
    )
    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/human-review-job",
        body=dict(
            assigneeEmailAddress="test2@test.com",
            name="test",
        ),
    )

    async def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        human_review_job=CreateHumanReviewJob(
            assignee_email_address=["test@test.com", "test2@test.com"],
            name="test",
        ),
    )


def test_serializes(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            testCaseBody=dict(
                d="2021-01-01T01:01:01",
                u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            ),
            testCaseOutput=dict(
                d="2021-01-01T01:01:01",
                u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            ),
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class ATestCase(BaseTestCase):
        d: datetime.datetime
        u: uuid.UUID

        def hash(self) -> str:
            return str(self.u)

    class AOutput(pydantic.BaseModel):
        d: datetime.datetime
        u: uuid.UUID

    def test_fn(test_case: ATestCase) -> AOutput:
        return AOutput(
            d=test_case.d,
            u=test_case.u,
        )

    run_test_suite(
        id="my-test-id",
        test_cases=[
            ATestCase(
                d=datetime.datetime(2021, 1, 1, 1, 1, 1),
                u=uuid.UUID("ed022d1e-d0f2-41e4-ad55-9df0479cb62d"),
            ),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_logs_errors_from_our_code(httpx_mock):
    """
    Tests that we propagate errors from our code (as opposed to the user's
    code, fn and evaluate_test_case).
    """
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
        body=None,
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    class SomeClass:
        pass

    # Output is not serializable, so this should raise an error
    # when we attempt to serialize and it should be logged
    def test_fn(test_case: MyTestCase) -> SomeClass:
        return SomeClass()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(
                input="hi",
            ),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["testExternalId"] == "my-test-id"
    assert error_req_body["runId"] == mock_run_id
    assert error_req_body["testCaseHash"] == "hi"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "TypeError"
    assert error_req_body["error"]["message"] == "Type is not JSON serializable: SomeClass"
    assert "TypeError: Type is not JSON serializable: SomeClass" in error_req_body["error"]["stacktrace"]


def test_skips_non_serializable_test_case_attributes(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            testCaseBody=dict(
                d="2021-01-01T01:01:01",
                u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            ),
            testCaseOutput="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    class SomeClass:
        pass

    @dataclasses.dataclass
    class TestCaseWithNonSerializableAttrs(BaseTestCase):
        # Serializable
        d: datetime.datetime
        u: uuid.UUID

        # Not serializable
        c: SomeClass

        def hash(self) -> str:
            return str(self.u)

    def test_fn(test_case: TestCaseWithNonSerializableAttrs) -> str:
        return str(test_case.u)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            TestCaseWithNonSerializableAttrs(
                d=datetime.datetime(2021, 1, 1, 1, 1, 1),
                u=uuid.UUID("ed022d1e-d0f2-41e4-ad55-9df0479cb62d"),
                c=SomeClass(),
            ),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "CI": "false",
    },
)
def test_sends_tracer_events(httpx_mock):
    timestamp = datetime.datetime(2021, 1, 1, 1, 1, 1).isoformat()
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/results/mock-result-id-1/events",
        body=dict(
            testCaseEvents=[
                dict(
                    message="a",
                    traceId=None,
                    timestamp=timestamp,
                    properties=dict(),
                    systemProperties=None,
                )
            ]
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/results/mock-result-id-2/events",
        body=dict(
            testCaseEvents=[
                dict(
                    message="b",
                    traceId=None,
                    timestamp=timestamp,
                    properties=dict(),
                    systemProperties=None,
                )
            ]
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    # initialize the tracer outside the test function
    # this ensures the context variables are being accessed inside send_event
    tracer = AutoblocksTracer("test")

    async def test_fn(test_case: MyTestCase) -> str:
        if test_case.input == "a":
            # simulate doing more work than b to make sure context var is working correctly
            await asyncio.sleep(1)
        tracer.send_event(message=test_case.input, timestamp=timestamp)
        return test_case.input + "!"

    test_cases = [
        MyTestCase(input="a"),
        MyTestCase(input="b"),
    ]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[],
        fn=test_fn,
        # we want test cases to run in parallel to ensure context var is working correctly
        max_test_case_concurrency=len(test_cases),
    )


def test_repeated_test_cases(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    # We should have three results for A
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-0",
            # test_case_config should not be in the serialized body
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-1",
            # test_case_config should not be in the serialized body
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-2",
            # test_case_config should not be in the serialized body
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-3"),
    )

    # We should have one result for B
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-4"),
    )

    # We should have 3 evals for A
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-0",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-1",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a-2",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )

    # We should have one eval for B
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            evaluatorExternalId="my-evaluator",
            score=0.98,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )

    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class SomeTestCase(BaseTestCase):
        """
        Unfortunately, users will need to specify the test_case_config
        field themselves. Ideally we would make BaseTestCase a dataclass
        and add this field as optional with a default, like:

        @dataclasses.dataclass
        class BaseTestCase:
            test_case_config: TestCaseConfig = dataclasses.field(default_factory=TestCaseConfig)

        But then users would not be able to inherit from BaseTestCase and have non-default fields
        on their own test case dataclass. This is due to how inheritance works for dataclasses:

        * https://docs.python.org/3/library/dataclasses.html#inheritance
        * https://stackoverflow.com/q/51575931

        This could be worked around by making BaseTestCase keyword-only via kw_only=True, but
        this was only added in Python 3.10, and we want to support 3.9 until it's closer to
        end of life.
        """

        input: str

        test_case_config: Optional[TestCaseConfig] = None

        def hash(self) -> str:
            return self.input

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        def evaluate_test_case(self, test_case: SomeTestCase, output: str) -> Evaluation:
            return Evaluation(score=ord(test_case.input) / 100)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            SomeTestCase(
                test_case_config=TestCaseConfig(
                    repeat_num_times=3,
                ),
                input="a",
            ),
            SomeTestCase(
                input="b",
            ),
        ],
        evaluators=[
            MyEvaluator(),
        ],
        fn=lambda test_case: test_case.input + "!",
        max_test_case_concurrency=1,
    )


def test_handles_evaluators_implementing_base_evaluator(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="0.5",
            testCaseBody=dict(x=0.5),
            testCaseOutput="whatever",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="0.5",
            evaluatorExternalId="my-combined-evaluator",
            score=0.5,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

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

    def test_fn(test_case: SomeTestCase) -> str:
        return "whatever"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            SomeTestCase(
                x=0.5,
            ),
        ],
        evaluators=[
            MyCombinedEvaluator(),
        ],
        fn=test_fn,
    )


def test_evaluators_with_optional_evaluations(httpx_mock):
    mock_run_id = str(uuid.uuid4())

    class RuleLevel(StrEnum):
        CRITICAL = "critical"
        MEDIUM = "medium"
        LOW = "low"

    @dataclasses.dataclass
    class Rule:
        level: RuleLevel
        rule: str

    @dataclasses.dataclass
    class TestCase(BaseTestCase):
        input: str
        rules: list[Rule]

        def hash(self):
            return md5(self.input)

    @dataclasses.dataclass
    class Output:
        actions: list[str]

    class RuleEvaluator(BaseTestEvaluator, abc.ABC):
        @property
        @abc.abstractmethod
        def level(self) -> RuleLevel:
            pass

        @property
        def id(self) -> str:
            return f"rule-evaluator-{self.level.value}"

        def _rule_passed(self, rule: Rule, output: Output) -> bool:
            """
            Use an LLM to determine if the rule was followed based on the output actions.
            """
            return False

        def evaluate_test_case(self, test_case: TestCase, output: Output) -> Optional[Evaluation]:
            rules = [rule for rule in test_case.rules if rule.level == self.level]
            if not rules:
                return None

            failed_rules = []

            for rule in rules:
                if not self._rule_passed(rule, output):
                    failed_rules.append(rule)

            return Evaluation(
                score=0 if failed_rules else 1,
                threshold=Threshold(gte=1),
                metadata=dict(failed_rules=[rule.rule for rule in failed_rules]) if failed_rules else None,
            )

    class CriticalLevelRuleEvaluator(RuleEvaluator):
        level = RuleLevel.CRITICAL

    class MediumLevelRuleEvaluator(RuleEvaluator):
        level = RuleLevel.MEDIUM

    class LowLevelRuleEvaluator(RuleEvaluator):
        level = RuleLevel.LOW

    def test_fn(test_case: TestCase) -> Output:
        return Output(
            # Some list of actions the agent took
            actions=[test_case.input]
        )

    test_cases = [
        TestCase(
            input="1",
            rules=[
                Rule(
                    level=RuleLevel.CRITICAL,
                    rule="this really, really shouldn't happen",
                ),
                Rule(
                    level=RuleLevel.CRITICAL,
                    rule="this also really, really shouldn't happen",
                ),
                Rule(
                    level=RuleLevel.LOW,
                    rule="not ideal but whatever",
                ),
            ],
        ),
        TestCase(
            input="2",
            rules=[
                Rule(
                    level=RuleLevel.MEDIUM,
                    rule="this is a bit concerning",
                ),
            ],
        ),
    ]

    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash=md5("1"),
            testCaseBody=dict(
                input="1",
                rules=[
                    dict(
                        level="critical",
                        rule="this really, really shouldn't happen",
                    ),
                    dict(
                        level="critical",
                        rule="this also really, really shouldn't happen",
                    ),
                    dict(
                        level="low",
                        rule="not ideal but whatever",
                    ),
                ],
            ),
            testCaseOutput=dict(actions=["1"]),
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash=md5("2"),
            testCaseBody=dict(
                input="2",
                rules=[
                    dict(
                        level="medium",
                        rule="this is a bit concerning",
                    ),
                ],
            ),
            testCaseOutput=dict(actions=["2"]),
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash=md5("1"),
            evaluatorExternalId="rule-evaluator-critical",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                failed_rules=[
                    "this really, really shouldn't happen",
                    "this also really, really shouldn't happen",
                ]
            ),
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash=md5("1"),
            evaluatorExternalId="rule-evaluator-low",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(failed_rules=["not ideal but whatever"]),
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash=md5("2"),
            evaluatorExternalId="rule-evaluator-medium",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(failed_rules=["this is a bit concerning"]),
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            CriticalLevelRuleEvaluator(),
            MediumLevelRuleEvaluator(),
            LowLevelRuleEvaluator(),
        ],
        fn=test_fn,
    )


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.value: "another-test-id",
    },
)
def test_alignment_mode_skips_test_suite(httpx_mock):
    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    # Nothing should have happened because this test suite
    # should have been skipped
    assert len(httpx_mock.get_requests()) == 0


def test_alignment_mode_without_test_case_hash(httpx_mock):
    test_id = "my-test-id"
    run_id = str(uuid.uuid4())
    test_case_a = MyTestCase(input="a")
    test_case_b = MyTestCase(input="b")

    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId=test_id,
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId=test_id,
            runId=run_id,
            testCaseHash=test_case_a.hash(),
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    httpx_mock.add_response()

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.value: test_id,
        },
    ):
        run_test_suite(
            id=test_id,
            test_cases=[test_case_a, test_case_b],
            evaluators=[],
            fn=test_fn,
            max_test_case_concurrency=1,
        )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/info",
            body=dict(
                language="python",
                runTestSuiteCalledFromDirectory=os.path.dirname(__file__),
                testCaseHashes=[test_case_a.hash(), test_case_b.hash()],
            ),
        ),
        dict(
            path="/start",
            body=dict(
                testExternalId=test_id,
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        # It should have run the first test case since no hash was specified
        dict(
            path="/results",
            body=dict(
                testExternalId=test_id,
                runId=run_id,
                testCaseHash=test_case_a.hash(),
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId=test_id,
                runId=run_id,
            ),
        ),
    ]

    assert requests[0]["body"]["runTestSuiteCalledFromDirectory"].endswith(
        "/python-sdk/tests/autoblocks",
    )


def test_alignment_mode_with_test_case_hash(httpx_mock):
    test_id = "my-test-id"
    run_id = str(uuid.uuid4())
    test_case_a = MyTestCase(input="a")
    test_case_b = MyTestCase(input="b")

    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId=test_id,
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId=test_id,
            runId=run_id,
            testCaseHash=test_case_b.hash(),
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    httpx_mock.add_response()

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.value: test_id,
            AutoblocksEnvVar.ALIGN_TEST_CASE_HASH.value: test_case_b.hash(),
        },
    ):
        run_test_suite(
            id=test_id,
            test_cases=[test_case_a, test_case_b],
            evaluators=[],
            fn=test_fn,
            max_test_case_concurrency=1,
        )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/info",
            body=dict(
                language="python",
                runTestSuiteCalledFromDirectory=os.path.dirname(__file__),
                testCaseHashes=[test_case_a.hash(), test_case_b.hash()],
            ),
        ),
        dict(
            path="/start",
            body=dict(
                testExternalId=test_id,
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        # Test case a should have been skipped
        dict(
            path="/results",
            body=dict(
                testExternalId=test_id,
                runId=run_id,
                testCaseHash=test_case_b.hash(),
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId=test_id,
                runId=run_id,
            ),
        ),
    ]

    assert requests[0]["body"]["runTestSuiteCalledFromDirectory"].endswith(
        "/python-sdk/tests/autoblocks",
    )


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.FILTERS_TEST_SUITES.value: json.dumps(["random"]),
    },
)
def test_filters_test_suites_skips_test(httpx_mock):
    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    # Nothing should have happened because this test suite
    # should have been skipped
    assert len(httpx_mock.get_requests()) == 0


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.FILTERS_TEST_SUITES.value: json.dumps(["test"]),
    },
)
def test_filters_test_suites_filters_tests(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )

    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=lambda t: t.input + "!",
        max_test_case_concurrency=1,
    )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.FILTERS_TEST_SUITES.value: json.dumps(["random", "test"]),
    },
)
def test_filters_test_suites_filters_tests_multiple_filters(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )

    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=lambda t: t.input + "!",
        max_test_case_concurrency=1,
    )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.FILTERS_TEST_SUITES.value: json.dumps(["my-test-id"]),
    },
)
def test_filters_test_suites_filters_tests_exact_match(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )

    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=lambda t: t.input + "!",
        max_test_case_concurrency=1,
    )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


@mock.patch.dict(
    os.environ,
    {
        AutoblocksEnvVar.OVERRIDES_TESTS_AND_HASHES.value: json.dumps({"another-test-id": []}),
    },
)
def test_tests_and_hashes_overrides_skips_test(httpx_mock):
    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
    )

    # Nothing should have happened because this test suite
    # should have been skipped
    assert len(httpx_mock.get_requests()) == 0


@mock.patch.dict(
    os.environ,
    {
        # Only test case a should be run
        AutoblocksEnvVar.OVERRIDES_TESTS_AND_HASHES.value: json.dumps({"my-test-id": []}),
    },
)
def test_tests_and_hashes_overrides_with_empty_value(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="b",
            testCaseBody=dict(input="b"),
            testCaseOutput="b!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )

    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=lambda t: t.input + "!",
        max_test_case_concurrency=1,
    )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


@mock.patch.dict(
    os.environ,
    {
        # Only test case a should be run
        AutoblocksEnvVar.OVERRIDES_TESTS_AND_HASHES.value: json.dumps({"my-test-id": ["a"]}),
    },
)
def test_tests_and_hashes_overrides_with_non_empty_value(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )

    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            # Test case b will be skipped
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=lambda t: t.input + "!",
        max_test_case_concurrency=1,
    )

    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]

    assert requests == [
        dict(
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=None,
                gridSearchParamsCombo=None,
            ),
        ),
        dict(
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
        ),
        dict(
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        ),
    ]


def test_run_stops_if_start_fails(httpx_mock):
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        status_code=403,
    )

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(
                input="a",
            ),
        ],
        evaluators=[],
        fn=lambda test_case: test_case.input + "!",
        max_test_case_concurrency=1,
    )

    # we retry the start request 3 times and all calls should be to /start
    assert len(httpx_mock.get_requests()) == 3
    for req in httpx_mock.get_requests():
        assert req.url.path == "/start"
        assert req.method == "POST"


def test_sync_before_evaluators_hook(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-1",
            score=0.1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-2",
            score=0.2,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class BeforeEvaluatorOutput1:
        x: float

    @dataclasses.dataclass
    class BeforeEvaluatorOutput2:
        y: float

    @dataclasses.dataclass
    class HookResults:
        hook1: BeforeEvaluatorOutput1
        hook2: BeforeEvaluatorOutput2

    class Evaluator1(BaseTestEvaluator):
        id = "evaluator-1"

        def evaluate_test_case(
            self,
            test_case: MyTestCase,
            output: str,
            hook_results: HookResults,
        ) -> Evaluation:
            return Evaluation(score=hook_results.hook1.x)

    class Evaluator2(BaseTestEvaluator):
        id = "evaluator-2"

        async def evaluate_test_case(
            self,
            test_case: MyTestCase,
            output: str,
            hook_results: HookResults,
        ) -> Evaluation:
            await asyncio.sleep(0.1)
            return Evaluation(score=hook_results.hook2.y)

    num_times_hook_called = 0

    def before_evaluators_hook(
        test_case: MyTestCase,
        output: str,
    ) -> HookResults:
        nonlocal num_times_hook_called
        num_times_hook_called += 1
        return HookResults(
            hook1=BeforeEvaluatorOutput1(x=0.1),
            hook2=BeforeEvaluatorOutput2(y=0.2),
        )

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[
            Evaluator1(),
            Evaluator2(),
        ],
        fn=lambda test_case: test_case.input + "!",
        before_evaluators_hook=before_evaluators_hook,
    )

    assert num_times_hook_called == 1


def test_async_before_evaluators_hook(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-1",
            score=0.1,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            evaluatorExternalId="evaluator-2",
            score=0.2,
            threshold=None,
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class BeforeEvaluatorOutput1:
        x: float

    @dataclasses.dataclass
    class BeforeEvaluatorOutput2:
        y: float

    @dataclasses.dataclass
    class HookResults:
        hook1: BeforeEvaluatorOutput1
        hook2: BeforeEvaluatorOutput2

    class Evaluator1(BaseTestEvaluator):
        id = "evaluator-1"

        def evaluate_test_case(
            self,
            test_case: MyTestCase,
            output: str,
            hook_results: HookResults,
        ) -> Evaluation:
            return Evaluation(score=hook_results.hook1.x)

    class Evaluator2(BaseTestEvaluator):
        id = "evaluator-2"

        async def evaluate_test_case(
            self,
            test_case: MyTestCase,
            output: str,
            hook_results: HookResults,
        ) -> Evaluation:
            await asyncio.sleep(0.1)
            return Evaluation(score=hook_results.hook2.y)

    num_times_hook_called = 0

    async def before_evaluators_hook(
        test_case: MyTestCase,
        output: str,
    ) -> HookResults:
        await asyncio.sleep(0.1)
        nonlocal num_times_hook_called
        num_times_hook_called += 1
        return HookResults(
            hook1=BeforeEvaluatorOutput1(x=0.1),
            hook2=BeforeEvaluatorOutput2(y=0.2),
        )

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[
            Evaluator1(),
            Evaluator2(),
        ],
        fn=lambda test_case: test_case.input + "!",
        before_evaluators_hook=before_evaluators_hook,
    )

    assert num_times_hook_called == 1


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_prompt_manager_revision_usage(httpx_mock):
    mock_run_id = str(uuid.uuid4())

    class MyPromptParams(pydantic.BaseModel):
        pass

    class MyTemplateRenderer(TemplateRenderer):
        __name_mapper__ = {}

    class MyToolRenderer(ToolRenderer):
        __name_mapper__ = {}

    class MyExecutionContext(
        PromptExecutionContext[
            MyPromptParams,
            MyTemplateRenderer,
            MyToolRenderer,
        ],
    ):
        __params_class__ = MyPromptParams
        __template_renderer_class__ = MyTemplateRenderer
        __tool_renderer_class__ = MyToolRenderer

    class PromptManagerA(
        AutoblocksPromptManager[MyExecutionContext],
    ):
        __prompt_id__ = "prompt-a"
        __prompt_major_version__ = "1"
        __execution_context_class__ = MyExecutionContext

    class PromptManagerB(
        AutoblocksPromptManager[MyExecutionContext],
    ):
        __prompt_id__ = "prompt-b"
        __prompt_major_version__ = "undeployed"
        __execution_context_class__ = MyExecutionContext

    # Mock the requests the prompt managers will make to fetch the prompts
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-a/major/1/minor/latest",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="prompt-a",
            version="1.1",
            revisionId="prompt-a-mock-revision-id",
            templates=[],
        ),
    )
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/prompts/prompt-b/major/undeployed/minor/0",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="prompt-b",
            version="revision:prompt-b-mock-revision-id",
            revisionId="prompt-b-mock-revision-id",
            templates=[],
        ),
    )

    mgr_a = PromptManagerA(minor_version="latest")
    mgr_b = PromptManagerB(minor_version="0")

    async def test_fn(test_case: MyTestCase) -> str:
        """
        y: prompt-a, prompt-b, prompt-a
        z: prompt-a
        """
        if test_case.input == "y":
            # simulate doing more work in y than z to ensure context var is working correctly
            await asyncio.sleep(1)

            with mgr_a.exec():
                pass
            with mgr_b.exec():
                pass

        with mgr_a.exec():
            pass

        return test_case.input + "!"

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            with mgr_b.exec():
                pass
            return Evaluation(score=0.97)

    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="y",
            testCaseBody=dict(input="y"),
            testCaseOutput="y!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=[
                dict(
                    entityExternalId="prompt-a",
                    entityType="prompt",
                    revisionId="prompt-a-mock-revision-id",
                    usedAt=mock.ANY,
                ),
                dict(
                    entityExternalId="prompt-b",
                    entityType="prompt",
                    revisionId="prompt-b-mock-revision-id",
                    usedAt=mock.ANY,
                ),
                dict(
                    entityExternalId="prompt-a",
                    entityType="prompt",
                    revisionId="prompt-a-mock-revision-id",
                    usedAt=mock.ANY,
                ),
            ],
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="z",
            testCaseBody=dict(input="z"),
            testCaseOutput="z!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=[
                dict(
                    entityExternalId="prompt-a",
                    entityType="prompt",
                    revisionId="prompt-a-mock-revision-id",
                    usedAt=mock.ANY,
                ),
            ],
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-2"),
    )
    expect_cli_post_request(
        httpx_mock,
        "/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="y",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=[
                dict(
                    entityExternalId="prompt-b",
                    entityType="prompt",
                    revisionId="prompt-b-mock-revision-id",
                    usedAt=mock.ANY,
                ),
            ],
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        "/evals",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="z",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=[
                dict(
                    entityExternalId="prompt-b",
                    entityType="prompt",
                    revisionId="prompt-b-mock-revision-id",
                    usedAt=mock.ANY,
                ),
            ],
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    test_cases = [
        MyTestCase(input="y"),
        MyTestCase(input="z"),
    ]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[MyEvaluator()],
        fn=test_fn,
        # we want test cases to run in parallel to ensure context var is working correctly
        max_test_case_concurrency=len(test_cases),
    )


def test_serialize(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="1-2",
            testCaseBody=dict(
                x=1,
                y=2,
                prod=2,
            ),
            testCaseOutput=dict(
                x=1,
                y=2,
                sum=3,
            ),
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class MyCustomTestCase(BaseTestCase):
        x: int
        y: int

        def hash(self):
            return f"{self.x}-{self.y}"

        def serialize(self):
            return dict(
                x=self.x,
                y=self.y,
                prod=self.x * self.y,
            )

    @dataclasses.dataclass
    class MyCustomOutput:
        x: int
        y: int

        def serialize(self):
            return dict(
                x=self.x,
                y=self.y,
                sum=self.x + self.y,
            )

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyCustomTestCase(x=1, y=2),
        ],
        fn=lambda test_case: MyCustomOutput(x=test_case.x, y=test_case.y),
    )


def test_serialize_for_human_review(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="1-2",
            testCaseBody=dict(
                x=1,
                y=2,
            ),
            testCaseOutput=dict(
                x=1,
                y=2,
            ),
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=[
                dict(name="x", value="1", contentType="text"),
                dict(name="y", value="2", contentType="markdown"),
                dict(name="sum", value="3", contentType="text"),
            ],
            testCaseHumanReviewOutputFields=[
                dict(name="x", value="1", contentType="text"),
                dict(name="y", value="2", contentType="text"),
                dict(name="sum", value="3", contentType="text"),
                dict(name="prod", value="2", contentType="text"),
                dict(name="diff", value="-1", contentType="text"),
            ],
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class MyCustomTestCase(BaseTestCase):
        x: int
        y: int

        def hash(self):
            return f"{self.x}-{self.y}"

        def serialize_for_human_review(self):
            return [
                HumanReviewField(
                    name="x",
                    value=f"{self.x}",
                ),
                HumanReviewField(
                    name="y",
                    value=f"{self.y}",
                    content_type=HumanReviewFieldContentType.MARKDOWN,
                ),
                HumanReviewField(
                    name="sum",
                    value=f"{self.x + self.y}",
                ),
            ]

    @dataclasses.dataclass
    class MyCustomOutput:
        x: int
        y: int

        def serialize_for_human_review(self):
            return [
                HumanReviewField(
                    name="x",
                    value=f"{self.x}",
                ),
                HumanReviewField(
                    name="y",
                    value=f"{self.y}",
                ),
                HumanReviewField(
                    name="sum",
                    value=f"{self.x + self.y}",
                ),
                HumanReviewField(
                    name="prod",
                    value=f"{self.x * self.y}",
                ),
                HumanReviewField(
                    name="diff",
                    value=f"{self.x - self.y}",
                ),
            ]

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyCustomTestCase(x=1, y=2),
        ],
        fn=lambda test_case: MyCustomOutput(x=test_case.x, y=test_case.y),
    )


def test_serialize_dataset_item_id(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    mock_dataset_item_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="1-2",
            testCaseBody=dict(
                x=1,
                y=2,
            ),
            testCaseOutput="1-2",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=mock_dataset_item_id,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    @dataclasses.dataclass
    class MyCustomTestCase(BaseTestCase):
        x: int
        y: int

        def hash(self):
            return f"{self.x}-{self.y}"

        def serialize_dataset_item_id(self):
            return mock_dataset_item_id

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyCustomTestCase(x=1, y=2),
        ],
        fn=lambda test_case: f"{test_case.x}-{test_case.y}",
    )


def test_grid_search_params(httpx_mock):
    mock_grid_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/grids",
        body=dict(
            gridSearchParams=dict(
                x=["x1", "x2"],
                y=["y1", "y2"],
            ),
        ),
        json=dict(id=mock_grid_id),
    )

    for combo in [
        dict(x="x1", y="y1"),
        dict(x="x1", y="y2"),
        dict(x="x2", y="y1"),
        dict(x="x2", y="y2"),
    ]:
        mock_run_id = uuid.uuid4().hex
        expect_cli_post_request(
            httpx_mock,
            path="/start",
            body=dict(
                testExternalId="my-test-id",
                gridSearchRunGroupId=mock_grid_id,
                gridSearchParamsCombo=combo,
            ),
            json=dict(id=mock_run_id),
        )
        expect_cli_post_request(
            httpx_mock,
            path="/results",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput=f"a-{combo['x']}-{combo['y']}!",
                testCaseDurationMs=ANY_NUMBER,
                testCaseRevisionUsage=None,
                testCaseHumanReviewInputFields=None,
                testCaseHumanReviewOutputFields=None,
                datasetItemId=None,
            ),
            json=dict(id="mock-result-id-1"),
        )
        expect_cli_post_request(
            httpx_mock,
            path="/end",
            body=dict(
                testExternalId="my-test-id",
                runId=mock_run_id,
            ),
        )

    def test_fn(test_case: MyTestCase) -> str:
        ctx = grid_search_ctx()
        if ctx is not None:
            return f"{test_case.input}-{ctx['x']}-{ctx['y']}!"
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        grid_search_params=dict(
            x=["x1", "x2"],
            y=["y1", "y2"],
        ),
    )


def test_exceptions_as_outputs(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput=ANY_STRING,
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    def test_fn(test_case: MyTestCase) -> Union[Exception, float]:
        try:
            return 1 / 0
        except Exception as err:
            return err

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        fn=test_fn,
    )

    # Get the testCaseOutput field from the /results request and
    # check it has the expected traceback
    requests = [dict(path=req.url.path, body=decode_request_body(req)) for req in httpx_mock.get_requests()]
    results_req = [r for r in requests if r["path"] == "/results"][0]
    output = results_req["body"]["testCaseOutput"]
    assert output.startswith("Traceback (most recent call last):")
    assert "ZeroDivisionError: division by zero" in output


def test_retry_on_timeout_errors(httpx_mock):
    """Test that retry_count parameter retries test cases on timeout/connection errors."""

    mock_run_id = str(uuid.uuid4())

    # Expect start request
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    # Expect results request (after successful retry)
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
            testCaseHash="a",
            testCaseBody=dict(input="a"),
            testCaseOutput="a!",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )

    # Expect end request
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    # Mock the test function to fail twice then succeed
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            # First two calls fail with timeout
            raise httpx.TimeoutException("Request timed out")
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=3,  # Allow up to 3 retries
    )

    # Should have been called 3 times (2 failures + 1 success)
    assert call_count == 3

    # Verify all expected requests were made
    requests = httpx_mock.get_requests()
    assert len(requests) == 3  # start, results, end


def test_retry_exhausted_reports_error(httpx_mock):
    """Test that when retries are exhausted, the error is properly reported."""

    mock_run_id = str(uuid.uuid4())

    # Expect start request
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    # Expect error request (after retries exhausted)
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        body=None,  # Will verify content below
    )

    # Expect end request
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    # Mock the test function to always fail with timeout
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("Request timed out")

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=2,  # Allow up to 2 retries
    )

    # Should have been called 3 times (2 retries + 1 original attempt)
    assert call_count == 3

    # Verify error was reported
    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["testExternalId"] == "my-test-id"
    assert error_req_body["runId"] == mock_run_id
    assert error_req_body["testCaseHash"] == "a"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "TimeoutException"
    assert error_req_body["error"]["message"] == "Request timed out"


def test_retry_only_on_specific_exceptions(httpx_mock):
    """Test that retry only happens for specific httpx exceptions, not all exceptions."""

    mock_run_id = str(uuid.uuid4())

    # Expect start request
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    # Expect error request (no retry for ValueError)
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        body=None,
    )

    # Expect end request
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    # Mock the test function to fail with ValueError (should not retry)
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Not a timeout error")

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=3,  # Allow up to 3 retries
    )

    # Should have been called only once (no retries for ValueError)
    assert call_count == 1

    # Verify error was reported
    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "Not a timeout error"


def test_retry_count_zero_no_retry(httpx_mock):
    """Test that retry_count=0 (default) doesn't retry on timeout errors."""

    mock_run_id = str(uuid.uuid4())

    # Expect start request
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id=mock_run_id),
    )

    # Expect error request (no retry)
    expect_cli_post_request(
        httpx_mock,
        path="/errors",
        body=None,
    )

    # Expect end request
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId=mock_run_id,
        ),
    )

    # Mock the test function to fail with timeout
    call_count = 0

    def test_fn(test_case: MyTestCase) -> str:
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("Request timed out")

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=test_fn,
        max_test_case_concurrency=1,
        retry_count=0,  # No retries
    )

    # Should have been called only once (no retries)
    assert call_count == 1

    # Verify error was reported
    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["error"]["name"] == "TimeoutException"
    assert error_req_body["error"]["message"] == "Request timed out"
