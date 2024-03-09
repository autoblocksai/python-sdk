import asyncio
import dataclasses
import datetime
import os
import uuid
from unittest import mock

import pydantic
import pytest

from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.models import Threshold
from autoblocks.testing.run import run_test_suite
from autoblocks.tracer import AutoblocksTracer
from tests.autoblocks.util import decode_request_body
from tests.autoblocks.util import make_expected_body

CLI_SERVER_ADDRESS = "http://localhost:8080"


@pytest.fixture(autouse=True)
def mock_cli_server_address_env_var():
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.CLI_SERVER_ADDRESS.value: CLI_SERVER_ADDRESS,
        },
    ):
        yield


@dataclasses.dataclass()
class MyTestCase(BaseTestCase):
    input: str

    def hash(self) -> str:
        return self.input


def test_no_test_cases(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[],
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
    assert req_body["error"]["message"] == "[my-test-id] No test cases provided."
    assert "AssertionError: [my-test-id] No test cases provided." in req_body["error"]["stacktrace"]


def test_invalid_test_cases(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[1, 2, 3],
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


def test_invalid_evaluators(httpx_mock):
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[1, 2, 3],
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


def test_error_in_test_fn(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/errors",
        method="POST",
        status_code=200,
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    def test_fn(test_case: MyTestCase):
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
    assert error_req_body["testCaseHash"] == "b"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_body["error"]["stacktrace"]


def test_error_in_async_test_fn(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/errors",
        method="POST",
        status_code=200,
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    async def test_fn(test_case: MyTestCase):
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
    assert error_req_body["testCaseHash"] == "b"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_body["error"]["stacktrace"]


def test_error_in_evaluator(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="my-sync-evaluator",
                score=0.5,
                threshold=dict(lt=0.6, lte=None, gt=None, gte=None),
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="my-async-evaluator",
                score=0.6,
                threshold=dict(lt=0.7, lte=None, gt=None, gte=None),
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )

    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/errors",
        method="POST",
        status_code=200,
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    def test_fn(test_case: MyTestCase):
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
    assert error_req_sync["testCaseHash"] == "b"
    assert error_req_sync["evaluatorExternalId"] == "my-sync-evaluator"
    assert error_req_sync["error"]["name"] == "ValueError"
    assert error_req_sync["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_sync["error"]["stacktrace"]

    assert error_req_async["testExternalId"] == "my-test-id"
    assert error_req_async["testCaseHash"] == "a"
    assert error_req_async["evaluatorExternalId"] == "my-async-evaluator"
    assert error_req_async["error"]["name"] == "ValueError"
    assert error_req_async["error"]["message"] == "a!"
    assert "ValueError: a!" in error_req_async["error"]["stacktrace"]


def test_no_evaluators(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    def test_fn(test_case: MyTestCase):
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


def test_with_evaluators(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=dict(reason="because"),
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=dict(reason="because"),
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    def test_fn(test_case: MyTestCase):
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
    httpx_mock.add_response()

    def test_fn(test_case: MyTestCase):
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
            dict(testExternalId="my-test-id"),
        ),
        (
            "/results",
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
        (
            "/results",
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
            ),
        ),
        (
            "/evals",
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
        (
            "/end",
            dict(testExternalId="my-test-id"),
        ),
    ]


def test_async_test_fn(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    async def test_fn(test_case: MyTestCase):
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
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/evals",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                evaluatorExternalId="evaluator-b",
                score=1,
                threshold=None,
                metadata=None,
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    def test_fn(test_case: MyTestCase):
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


def test_serializes(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
                testCaseBody=dict(
                    d="2021-01-01T01:01:01",
                    u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
                ),
                testCaseOutput=dict(
                    d="2021-01-01T01:01:01",
                    u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
                ),
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    @dataclasses.dataclass()
    class ATestCase(BaseTestCase):
        d: datetime.datetime
        u: uuid.UUID

        def hash(self) -> str:
            return str(self.u)

    class AOutput(pydantic.BaseModel):
        d: datetime.datetime
        u: uuid.UUID

    def test_fn(test_case: ATestCase):
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
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/errors",
        method="POST",
        status_code=200,
        # Content will be asserted below since we
        # can't match on the stacktrace exactly
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
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
    assert error_req_body["testCaseHash"] == "hi"
    assert error_req_body["evaluatorExternalId"] is None
    assert error_req_body["error"]["name"] == "TypeError"
    assert error_req_body["error"]["message"] == "Type is not JSON serializable: SomeClass"
    assert "TypeError: Type is not JSON serializable: SomeClass" in error_req_body["error"]["stacktrace"]


def test_skips_non_serializable_test_case_attributes(httpx_mock):
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
                testCaseBody=dict(
                    d="2021-01-01T01:01:01",
                    u="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
                ),
                testCaseOutput="ed022d1e-d0f2-41e4-ad55-9df0479cb62d",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    class SomeClass:
        pass

    @dataclasses.dataclass()
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


def test_deprecated_max_evaluator_concurrency(httpx_mock):
    """
    Test that we can still pass the deprecated max_evaluator_concurrency argument
    """
    httpx_mock.add_response()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[],
        fn=lambda _: "hello",
        max_test_case_concurrency=1,
        max_evaluator_concurrency=5,
    )


def test_sends_tracer_events(httpx_mock):
    timestamp = datetime.datetime(2021, 1, 1, 1, 1, 1).isoformat()
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/start",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/events",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                event=dict(message="a", traceId=None, timestamp=timestamp, properties=dict()),
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                testCaseBody=dict(input="a"),
                testCaseOutput="a!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/events",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                event=dict(message="b", traceId=None, timestamp=timestamp, properties=dict()),
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/results",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
                testCaseHash="b",
                testCaseBody=dict(input="b"),
                testCaseOutput="b!",
            ),
        ),
    )
    httpx_mock.add_response(
        url=f"{CLI_SERVER_ADDRESS}/end",
        method="POST",
        status_code=200,
        match_content=make_expected_body(
            dict(
                testExternalId="my-test-id",
            )
        ),
    )

    async def test_fn(test_case: MyTestCase):
        tracer = AutoblocksTracer("test")
        if test_case.input == "a":
            # simulate doing more work than b to make sure context manager is working correctly
            await asyncio.sleep(1)
        tracer.send_event(message=test_case.input, timestamp=timestamp)
        return test_case.input + "!"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[],
        fn=test_fn,
        # concurrency is set to 2 because we want test cases to run in parallel
        # to ensure context manager is working correctly
        max_test_case_concurrency=2,
    )
