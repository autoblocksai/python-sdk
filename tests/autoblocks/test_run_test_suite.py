import dataclasses
import json
import os
from unittest import mock

import pytest

from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.models import BaseEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.models import Threshold
from autoblocks.testing.run import run_test_suite
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


def test_no_test_cases():
    # This should not make any calls to the server
    # because it will exit early due to not having any test cases
    run_test_suite(
        id="test_id",
        test_cases=[],
        evaluators=[],
        fn=lambda _: None,
        max_test_case_concurrency=1,
        max_evaluator_concurrency=1,
    )


def test_invalid_test_cases():
    # This should not make any calls to the server
    # because it will exit early due to the invalid test cases
    run_test_suite(
        id="test_id",
        test_cases=[1, 2, 3],
        evaluators=[],
        fn=lambda _: None,
        max_test_case_concurrency=1,
        max_evaluator_concurrency=1,
    )


def test_invalid_evaluators():
    # This should not make any calls to the server
    # because it will exit early due to the invalid evaluators
    run_test_suite(
        id="test_id",
        test_cases=[
            MyTestCase(input="a"),
        ],
        evaluators=[1, 2, 3],
        fn=lambda _: None,
        max_test_case_concurrency=1,
        max_evaluator_concurrency=1,
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
    error_req_body = json.loads(error_req.content.decode())

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

    class MyEvaluator(BaseEvaluator):
        id = "my-evaluator"

        def evaluate(self, test_case: MyTestCase, output: str) -> Evaluation:
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
    for r in requests:
        print(r, json.loads(r.content.decode()))
    error_req = [r for r in requests if r.url.path == "/errors"][0]
    error_req_body = json.loads(error_req.content.decode())

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

    class EvaluatorA(BaseEvaluator):
        id = "evaluator-a"

        def evaluate(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0)

    class EvaluatorB(BaseEvaluator):
        id = "evaluator-b"

        def evaluate(self, test_case: MyTestCase, output: str) -> Evaluation:
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

    class EvaluatorA(BaseEvaluator):
        id = "evaluator-a"

        async def evaluate(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0)

    class EvaluatorB(BaseEvaluator):
        id = "evaluator-b"

        async def evaluate(self, test_case: MyTestCase, output: str) -> Evaluation:
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
