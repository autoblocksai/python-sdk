import dataclasses
import os
from unittest import mock

import pytest

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.evaluators import BaseAutomaticBattle
from autoblocks.testing.evaluators import BaseHasAllSubstrings
from autoblocks.testing.evaluators import BaseManualBattle
from autoblocks.testing.evaluators import BaseRagasContextPrecision
from autoblocks.testing.evaluators import BaseRagasContextRecall
from autoblocks.testing.evaluators import BaseRagasFaithfulness
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import Threshold
from autoblocks.testing.run import run_test_suite
from tests.util import ANY_NUMBER
from tests.util import ANY_STRING
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import expect_cli_post_request


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


@pytest.fixture(autouse=True)
def non_mocked_hosts() -> list[str]:
    return ["api.openai.com"]


@dataclasses.dataclass
class MyTestCase(BaseTestCase):
    input: str
    expected_substrings: list[str]

    def hash(self) -> str:
        return self.input


@dataclasses.dataclass
class RagasTestCase(BaseTestCase):
    question: str
    expected_answer: str

    def hash(self) -> str:
        return self.question


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

    class HasAllSubstrings(BaseHasAllSubstrings[MyTestCase, str]):
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
            HasAllSubstrings(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_manual_battle_evaluator(httpx_mock):
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
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            evaluatorExternalId="battle",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=0.5),
            metadata=dict(
                reason=ANY_STRING,
                baseline="goodbye",
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

    class Battle(BaseManualBattle[MyTestCase, str]):
        id = "battle"
        criteria = "Choose the best greeting."

        def output_mapper(self, output: str) -> str:
            return output

        def baseline_mapper(self, test_case: MyTestCase) -> str:
            return "goodbye"

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


def test_automatic_battle_evaluator(httpx_mock):
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
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/test-suites/my-test-id/test-cases/hello world/baseline",
        method="GET",
        status_code=200,
        json={"baseline": "goodbye"},
    )
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/test-suites/my-test-id/test-cases/hello world/baseline",
        method="POST",
        status_code=200,
        match_json={"baseline": "hello world"},
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hello world",
            evaluatorExternalId="battle",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=0.5),
            metadata=dict(
                reason=ANY_STRING,
                baseline="goodbye",
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

    class Battle(BaseAutomaticBattle[MyTestCase, str]):
        id = "battle"
        criteria = "Choose the best greeting."

        def output_mapper(self, output: str) -> str:
            return output

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


def test_ragas_context_precision_evaluator(httpx_mock):
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
            testCaseHash="How tall is the Eiffel tower?",
            testCaseBody=dict(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
            testCaseOutput="300 meters",
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
            testCaseHash="How tall is the Eiffel tower?",
            evaluatorExternalId="context-precision",
            score=ANY_NUMBER,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=None,
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

    def test_fn(test_case: RagasTestCase) -> str:
        return test_case.expected_answer

    class ContextPrecision(BaseRagasContextPrecision[RagasTestCase, str]):
        id = "context-precision"
        threshold = Threshold(gte=1)

        def question_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def answer_mapper(self, output: str) -> str:
            return output

        def contexts_mapper(self, test_case: RagasTestCase, output: str) -> list[str]:
            return ["The eiffel tower stands 300 meters tall."]

        def ground_truth_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=[
            RagasTestCase(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
        ],
        evaluators=[
            ContextPrecision(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_ragas_context_recall_evaluator(httpx_mock):
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
            testCaseHash="How tall is the Eiffel tower?",
            testCaseBody=dict(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
            testCaseOutput="300 meters",
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
            testCaseHash="How tall is the Eiffel tower?",
            evaluatorExternalId="context-recall",
            score=ANY_NUMBER,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=None,
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

    def test_fn(test_case: RagasTestCase) -> str:
        return test_case.expected_answer

    class ContextPrecision(BaseRagasContextRecall[RagasTestCase, str]):
        id = "context-recall"
        threshold = Threshold(gte=1)

        def question_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def answer_mapper(self, output: str) -> str:
            return output

        def contexts_mapper(self, test_case: RagasTestCase, output: str) -> list[str]:
            return ["The eiffel tower stands 300 meters tall."]

        def ground_truth_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=[
            RagasTestCase(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
        ],
        evaluators=[
            ContextPrecision(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_ragas_faithfulness_evaluator(httpx_mock):
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
            testCaseHash="How tall is the Eiffel tower?",
            testCaseBody=dict(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
            testCaseOutput="300 meters",
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
            testCaseHash="How tall is the Eiffel tower?",
            evaluatorExternalId="faithfulness",
            score=ANY_NUMBER,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=None,
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

    def test_fn(test_case: RagasTestCase) -> str:
        return test_case.expected_answer

    class ContextPrecision(BaseRagasFaithfulness[RagasTestCase, str]):
        id = "faithfulness"
        threshold = Threshold(gte=1)

        def question_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def answer_mapper(self, output: str) -> str:
            return output

        def contexts_mapper(self, test_case: RagasTestCase, output: str) -> list[str]:
            return ["The eiffel tower stands 300 meters tall."]

        def ground_truth_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=[
            RagasTestCase(question="How tall is the Eiffel tower?", expected_answer="300 meters"),
        ],
        evaluators=[
            ContextPrecision(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )
