import dataclasses
import os
from textwrap import dedent
from unittest import mock

import pytest

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.evaluators import BaseAutomaticBattle
from autoblocks.testing.evaluators import BaseHasAllSubstrings
from autoblocks.testing.evaluators import BaseIsEquals
from autoblocks.testing.evaluators import BaseIsValidJSON
from autoblocks.testing.evaluators import BaseLLMJudge
from autoblocks.testing.evaluators import BaseManualBattle
from autoblocks.testing.evaluators import BaseNSFW
from autoblocks.testing.evaluators import BaseToxicity
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import EvaluationOverride
from autoblocks.testing.models import ScoreChoice
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


def test_is_equals_evaluator(httpx_mock):
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
            evaluatorExternalId="is-equals",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=None,
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hi world",
            testCaseBody=dict(input="hi world", expected_substrings=["hello", "world"]),
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
            testCaseHash="hi world",
            evaluatorExternalId="is-equals",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                expected_output="hi world",
                actual_output="hello world",
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
        return "hello world"

    class IsEquals(BaseIsEquals[MyTestCase, str]):
        id = "is-equals"

        def test_case_mapper(self, test_case: MyTestCase) -> str:
            return test_case.input

        def output_mapper(self, output: str) -> str:
            return output

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="hello world", expected_substrings=["hello", "world"]),
            MyTestCase(input="hi world", expected_substrings=["hello", "world"]),
        ],
        evaluators=[
            IsEquals(),
        ],
        fn=test_fn,
    )


def test_is_valid_json_evaluator(httpx_mock):
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
            evaluatorExternalId="is-valid-json",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(error="Expecting value: line 1 column 1 (char 0)"),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash='{"hi": "world"}',
            testCaseBody=dict(input='{"hi": "world"}', expected_substrings=["hi", "world"]),
            testCaseOutput='{"hi": "world"}',
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
            testCaseHash='{"hi": "world"}',
            evaluatorExternalId="is-valid-json",
            score=1,
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

    def test_fn(test_case: MyTestCase) -> str:
        return test_case.input

    class IsValidJSON(BaseIsValidJSON[MyTestCase, str]):
        id = "is-valid-json"

        def output_mapper(self, output: str) -> str:
            return output

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(input="hello world", expected_substrings=["hello", "world"]),
            MyTestCase(input='{"hi": "world"}', expected_substrings=["hi", "world"]),
        ],
        evaluators=[
            IsValidJSON(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_toxicity_evaluator(httpx_mock):
    @dataclasses.dataclass
    class TestCase(BaseTestCase):
        input: str

        def hash(self) -> str:
            return self.input

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
            testCaseHash="I hate you",
            testCaseBody=dict(input="I hate you"),
            testCaseOutput="I hate you",
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
            testCaseHash="I hate you",
            evaluatorExternalId="toxicity",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
            ),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="I love you",
            testCaseBody=dict(input="I love you"),
            testCaseOutput="I love you",
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
            testCaseHash="I love you",
            evaluatorExternalId="toxicity",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
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

    def test_fn(test_case: TestCase) -> str:
        return test_case.input

    class Toxicity(BaseToxicity[TestCase, str]):
        id = "toxicity"

        def output_mapper(self, output: str) -> str:
            return output

    run_test_suite(
        id="my-test-id",
        test_cases=[
            TestCase(input="I hate you"),
            TestCase(input="I love you"),
        ],
        evaluators=[
            Toxicity(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_nsfw_evaluator(httpx_mock):
    @dataclasses.dataclass
    class TestCase(BaseTestCase):
        input: str

        def hash(self) -> str:
            return self.input

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
            testCaseHash="shit",
            testCaseBody=dict(input="shit"),
            testCaseOutput="shit",
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
            testCaseHash="shit",
            evaluatorExternalId="nsfw",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
            ),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="I love you",
            testCaseBody=dict(input="I love you"),
            testCaseOutput="I love you",
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
            testCaseHash="I love you",
            evaluatorExternalId="nsfw",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
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

    def test_fn(test_case: TestCase) -> str:
        return test_case.input

    class NSFW(BaseNSFW[TestCase, str]):
        id = "nsfw"

        def output_mapper(self, output: str) -> str:
            return output

    run_test_suite(
        id="my-test-id",
        test_cases=[
            TestCase(input="shit"),
            TestCase(input="I love you"),
        ],
        evaluators=[
            NSFW(),
        ],
        fn=test_fn,
        max_test_case_concurrency=1,
    )


def test_llm_judge_evaluator(httpx_mock):
    @dataclasses.dataclass
    class TestCase(BaseTestCase):
        input: str

        def hash(self) -> str:
            return self.input

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
            testCaseHash="70",
            testCaseBody=dict(input="70"),
            testCaseOutput="70",
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
            testCaseHash="70",
            evaluatorExternalId="contains-zero",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
            ),
            revisionUsage=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="5",
            testCaseBody=dict(input="5"),
            testCaseOutput="5",
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
            testCaseHash="5",
            evaluatorExternalId="contains-zero",
            score=0,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
            metadata=dict(
                reason=ANY_STRING,
                prompt=ANY_STRING,
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

    def test_fn(test_case: TestCase) -> str:
        return test_case.input

    class ContainsZero(BaseLLMJudge[TestCase, str]):
        id = "contains-zero"
        threshold = Threshold(gte=1)
        score_choices = [
            ScoreChoice(
                value=1,
                name="Contains Zero",
            ),
            ScoreChoice(
                value=0,
                name="Does Not Contain Zero",
            ),
        ]

        def make_prompt(self, test_case: TestCase, output: str, recent_overrides: list[EvaluationOverride]) -> str:
            return dedent(
                f"""
            Does this output contain a zero?

            [Output]
            {output}
            """
            ).strip()

    run_test_suite(
        id="my-test-id",
        test_cases=[
            TestCase(input="70"),
            TestCase(input="5"),
        ],
        evaluators=[
            ContainsZero(),
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
