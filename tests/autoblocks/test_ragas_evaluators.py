import dataclasses
import os
from typing import Any
from unittest import mock

import pytest

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.evaluators import BaseRagasAnswerCorrectness
from autoblocks.testing.evaluators import BaseRagasAnswerRelevancy
from autoblocks.testing.evaluators import BaseRagasAnswerSemanticSimilarity
from autoblocks.testing.evaluators import BaseRagasContextEntitiesRecall
from autoblocks.testing.evaluators import BaseRagasContextPrecision
from autoblocks.testing.evaluators import BaseRagasContextRecall
from autoblocks.testing.evaluators import BaseRagasContextRelevancy
from autoblocks.testing.evaluators import BaseRagasFaithfulness
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import Threshold
from autoblocks.testing.run import run_test_suite
from tests.util import ANY_NUMBER
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


def make_expected_requests(evaluator_id: str, httpx_mock: Any) -> None:
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id="mock-run-id"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId="mock-run-id",
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
            runId="mock-run-id",
            testCaseHash="How tall is the Eiffel tower?",
            evaluatorExternalId=evaluator_id,
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
            runId="mock-run-id",
        ),
    )


@dataclasses.dataclass
class RagasTestCase(BaseTestCase):
    question: str
    expected_answer: str

    def hash(self) -> str:
        return self.question


test_cases = [RagasTestCase(question="How tall is the Eiffel tower?", expected_answer="300 meters")]


def function_to_test(test_case: RagasTestCase) -> str:
    return test_case.expected_answer


def test_ragas_context_precision_evaluator(httpx_mock):
    make_expected_requests("context-precision", httpx_mock)

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
        test_cases=test_cases,
        evaluators=[
            ContextPrecision(),
        ],
        fn=function_to_test,
    )


def test_ragas_context_recall_evaluator(httpx_mock):
    make_expected_requests("context-recall", httpx_mock)

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
        test_cases=test_cases,
        evaluators=[
            ContextPrecision(),
        ],
        fn=function_to_test,
    )


def test_ragas_faithfulness_evaluator(httpx_mock):
    make_expected_requests("faithfulness", httpx_mock)

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
        test_cases=test_cases,
        evaluators=[
            ContextPrecision(),
        ],
        fn=function_to_test,
    )


def test_ragas_answer_correctness_evaluator(httpx_mock):
    make_expected_requests("answer-correctness", httpx_mock)

    class AnswerCorrectness(BaseRagasAnswerCorrectness[RagasTestCase, str]):
        id = "answer-correctness"
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
        test_cases=test_cases,
        evaluators=[
            AnswerCorrectness(),
        ],
        fn=function_to_test,
    )


def test_ragas_answer_relevancy_evaluator(httpx_mock):
    make_expected_requests("answer-relevancy", httpx_mock)

    class AnswerRelevancy(BaseRagasAnswerRelevancy[RagasTestCase, str]):
        id = "answer-relevancy"
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
        test_cases=test_cases,
        evaluators=[
            AnswerRelevancy(),
        ],
        fn=function_to_test,
    )


def test_ragas_answer_semantic_similarity_evaluator(httpx_mock):
    make_expected_requests("answer-semantic-similarity", httpx_mock)

    class AnswerSemanticSimilarity(BaseRagasAnswerSemanticSimilarity[RagasTestCase, str]):
        id = "answer-semantic-similarity"
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
        test_cases=test_cases,
        evaluators=[
            AnswerSemanticSimilarity(),
        ],
        fn=function_to_test,
    )


def test_ragas_context_entities_recall_evaluator(httpx_mock):
    make_expected_requests("context-entities-recall", httpx_mock)

    class ContextEntitiesRecall(BaseRagasContextEntitiesRecall[RagasTestCase, str]):
        id = "context-entities-recall"
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
        test_cases=test_cases,
        evaluators=[
            ContextEntitiesRecall(),
        ],
        fn=function_to_test,
    )


def test_ragas_context_relevancy_evaluator(httpx_mock):
    make_expected_requests("context-relevancy", httpx_mock)

    class ContextRelevancy(BaseRagasContextRelevancy[RagasTestCase, str]):
        id = "context-relevancy"
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
        test_cases=test_cases,
        evaluators=[
            ContextRelevancy(),
        ],
        fn=function_to_test,
    )
