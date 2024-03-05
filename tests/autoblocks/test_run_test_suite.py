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
        max_evaluator_concurrency=1,
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
        max_evaluator_concurrency=1,
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
        max_evaluator_concurrency=1,
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
        max_evaluator_concurrency=1,
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
                evaluatorExternalId="my-evaluator",
                score=0.5,
                threshold=dict(lt=0.6, lte=None, gt=None, gte=None),
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

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            if test_case.input == "a":
                return Evaluation(
                    score=0.5,
                    threshold=Threshold(lt=0.6),
                )
            raise ValueError(output)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="a"),
            MyTestCase(input="b"),
        ],
        evaluators=[MyEvaluator()],
        fn=test_fn,
        max_test_case_concurrency=1,
        max_evaluator_concurrency=1,
    )

    requests = httpx_mock.get_requests()
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = decode_request_body(error_req)

    assert error_req_body["testExternalId"] == "my-test-id"
    assert error_req_body["testCaseHash"] == "b"
    assert error_req_body["evaluatorExternalId"] == "my-evaluator"
    assert error_req_body["error"]["name"] == "ValueError"
    assert error_req_body["error"]["message"] == "b!"
    assert "ValueError: b!" in error_req_body["error"]["stacktrace"]


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
        max_evaluator_concurrency=1,
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
            return Evaluation(score=0)

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
        max_evaluator_concurrency=1,
    )


def test_concurrency(httpx_mock):
    httpx_mock.add_response()

    def test_fn(test_case: MyTestCase):
        return test_case.input + "!"

    class EvaluatorA(BaseTestEvaluator):
        id = "evaluator-a"

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0)

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
        max_evaluator_concurrency=1,
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
            "/evals",
            dict(
                testExternalId="my-test-id",
                testCaseHash="a",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
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
                testCaseHash="b",
                evaluatorExternalId="evaluator-a",
                score=0,
                threshold=None,
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
        tracer = AutoblocksTracer("test")
        tracer.sendEvent("test")
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
        max_evaluator_concurrency=1,
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
        max_evaluator_concurrency=1,
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
        max_evaluator_concurrency=1,
    )
