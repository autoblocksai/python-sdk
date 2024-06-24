import dataclasses
import os
from unittest import mock

import pytest

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import ThirdPartyEnvVar
from autoblocks.testing.evaluators import HasAllSubstrings
from autoblocks.testing.evaluators import ManualBattle
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.run import run_test_suite
from tests.util import ANY_NUMBER
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import expect_cli_post_request
from tests.util import expect_openai_post_request


@pytest.fixture(autouse=True)
def mock_cli_server_address_env_var():
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.CLI_SERVER_ADDRESS.value: MOCK_CLI_SERVER_ADDRESS,
            AutoblocksEnvVar.API_KEY.value: "mock-api-key",
        },
    ):
        yield


@dataclasses.dataclass
class MyTestCase(BaseTestCase):
    input: str
    expected_substrings: list[str]

    def hash(self) -> str:
        return self.input


def test_has_all_substrings_evaluator(httpx_mock):
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            testCaseBody=dict(input="hello world", expected_substrings=["hello", "world"]),
            testCaseOutput="hello world",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            evaluatorExternalId="has-all-substrings",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(missing_substrings=[]),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="foo",
            testCaseBody=dict(input="foo", expected_substrings=["bar"]),
            testCaseOutput="foo",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="foo",
            evaluatorExternalId="has-all-substrings",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(missing_substrings=["bar"]),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input

    class MyHasAllSubstrings(HasAllSubstrings):

        id = "has-all-substrings"

        def test_case_mapper(self, test_case: MyTestCase) -> list[str]:
            return test_case.expected_substrings

        def output_mapper(self, output: str) -> str:
            return output

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="hello world", expected_substrings=["hello", "world"]),
            MyTestCase(input="foo", expected_substrings=["bar"]),
        ],
        evaluators=[
            MyHasAllSubstrings(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


@mock.patch.dict(
    os.environ,
    {
        ThirdPartyEnvVar.OPENAI_API_KEY.value: "mock-openai-api-key",
    },
)
def test_battle_evaluator(httpx_mock):
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            testCaseBody=dict(input="hello world", expected_substrings=[]),
            testCaseOutput="hello world",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
        ),
    )
    expect_openai_post_request(
        httpx_mock,
        response_message_content='{"reason": "This is the reason.", "result": "1"}',
        status_code=200,
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            evaluatorExternalId="battle",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=0.5),
            metadata=dict(
                reason="This is the reason.",
                baseline="goodbye world",
                challenger="hello world",
                criteria="Choose the best greeting.",
            ),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
        ),
    )

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input

    class Battle(ManualBattle):
        id = "battle"
        criteria = "Choose the best greeting."

        def output_mapper(self, output: str) -> str:
            return output

        def baseline_mapper(self, test_case: MyTestCase) -> str:
            return "goodbye world"

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="hello world", expected_substrings=[]),
        ],
        evaluators=[
            Battle(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )
