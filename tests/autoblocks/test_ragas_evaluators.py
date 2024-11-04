import dataclasses
import os
from typing import Any
from typing import List
from unittest import mock

import pytest
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper  # type: ignore[import-untyped]
from ragas.llms import LangchainLLMWrapper  # type: ignore[import-untyped]

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.evaluators import BaseRagasContextEntitiesRecall
from autoblocks.testing.evaluators import BaseRagasFactualCorrectness
from autoblocks.testing.evaluators import BaseRagasFaithfulness
from autoblocks.testing.evaluators import BaseRagasLLMContextPrecisionWithReference
from autoblocks.testing.evaluators import BaseRagasLLMContextRecall
from autoblocks.testing.evaluators import BaseRagasNoiseSensitivity
from autoblocks.testing.evaluators import BaseRagasNonLLMContextPrecisionWithReference
from autoblocks.testing.evaluators import BaseRagasNonLLMContextRecall
from autoblocks.testing.evaluators import BaseRagasResponseRelevancy
from autoblocks.testing.evaluators import BaseRagasSemanticSimilarity
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import Threshold
from autoblocks.testing.run import run_test_suite
from tests.util import ANY_NUMBER
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import expect_cli_post_request

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
evaluator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())


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


# apply this to all tests in this file
pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api.openai.com"])


def make_expected_requests(evaluator_id: str, httpx_mock: Any) -> None:
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
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
            testCaseBody=dict(
                question="How tall is the Eiffel tower?", expected_answer="The Eiffel Tower is 300 meters tall."
            ),
            testCaseOutput="The Eiffel Tower is 300 meters tall.",
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
            runId="mock-run-id",
            testCaseHash="How tall is the Eiffel tower?",
            evaluatorExternalId=evaluator_id,
            score=ANY_NUMBER,
            threshold=dict(lt=None, lte=None, gt=None, gte=1),
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
            runId="mock-run-id",
        ),
    )


@dataclasses.dataclass
class RagasTestCase(BaseTestCase):
    question: str
    expected_answer: str

    def hash(self) -> str:
        return self.question


test_cases = [
    RagasTestCase(question="How tall is the Eiffel tower?", expected_answer="The Eiffel Tower is 300 meters tall.")
]


def function_to_test(test_case: RagasTestCase) -> str:
    return test_case.expected_answer


def test_ragas_context_recall_evaluator(httpx_mock):
    make_expected_requests("context-recall", httpx_mock)

    class ContextRecall(BaseRagasLLMContextRecall[RagasTestCase, str]):
        id = "context-recall"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def response_mapper(self, output: str) -> str:
            return output

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> list[str]:
            return ["The eiffel tower stands 300 meters tall."]

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            ContextRecall(),
        ],
        fn=function_to_test,
    )


def test_ragas_factual_correctness_evaluator(httpx_mock):
    make_expected_requests("factual-correctness", httpx_mock)

    class FactualCorrectness(BaseRagasFactualCorrectness[RagasTestCase, str]):
        id = "factual-correctness"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def response_mapper(self, output: str) -> str:
            return output

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            FactualCorrectness(),
        ],
        fn=function_to_test,
    )


def test_ragas_faithfulness_evaluator(httpx_mock):
    make_expected_requests("faithfulness", httpx_mock)

    class Faithfulness(BaseRagasFaithfulness[RagasTestCase, str]):
        id = "faithfulness"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def response_mapper(self, output: str) -> str:
            return output

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            Faithfulness(),
        ],
        fn=function_to_test,
    )


def test_ragas_llm_context_recall_evaluator(httpx_mock):
    make_expected_requests("llm-context-recall", httpx_mock)

    class LLMContextRecall(BaseRagasLLMContextRecall[RagasTestCase, str]):
        id = "llm-context-recall"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def response_mapper(self, output: str) -> str:
            return output

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            LLMContextRecall(),
        ],
        fn=function_to_test,
    )


def test_ragas_non_llm_context_recall_evaluator(httpx_mock):
    make_expected_requests("non-llm-context-recall", httpx_mock)

    class NonLLMContextRecall(BaseRagasNonLLMContextRecall[RagasTestCase, str]):
        id = "non-llm-context-recall"
        threshold = Threshold(gte=1)

        def reference_contexts_mapper(self, test_case: RagasTestCase) -> List[str]:
            return ["The Eiffel Tower is 300 meters tall."]

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            NonLLMContextRecall(),
        ],
        fn=function_to_test,
    )


def test_ragas_response_relevancy_evaluator(httpx_mock):
    make_expected_requests("response-relevancy", httpx_mock)

    class ResponseRelevancy(BaseRagasResponseRelevancy[RagasTestCase, str]):
        id = "response-relevancy"
        threshold = Threshold(gte=1)
        llm = evaluator_llm
        embeddings = evaluator_embeddings

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def response_mapper(self, output: str) -> str:
            return output

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            ResponseRelevancy(),
        ],
        fn=function_to_test,
    )


def test_ragas_semantic_similarity_evaluator(httpx_mock):
    make_expected_requests("semantic-similarity", httpx_mock)

    class SemanticSimilarity(BaseRagasSemanticSimilarity[RagasTestCase, str]):
        id = "semantic-similarity"
        threshold = Threshold(gte=1)
        embeddings = evaluator_embeddings

        def response_mapper(self, output: str) -> str:
            return output

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            SemanticSimilarity(),
        ],
        fn=function_to_test,
    )


def test_ragas_noise_sensitivity_evaluator(httpx_mock):
    make_expected_requests("noise-sensitivity", httpx_mock)

    class NoiseSensitivity(BaseRagasNoiseSensitivity[RagasTestCase, str]):
        id = "noise-sensitivity"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def response_mapper(self, output: str) -> str:
            return output

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            NoiseSensitivity(),
        ],
        fn=function_to_test,
    )


def test_ragas_context_entities_recall_evaluator(httpx_mock):
    make_expected_requests("context-entities-recall", httpx_mock)

    class ContextEntitiesRecall(BaseRagasContextEntitiesRecall[RagasTestCase, str]):
        id = "context-entities-recall"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall in Paris, France."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            ContextEntitiesRecall(),
        ],
        fn=function_to_test,
    )


def test_ragas_llm_context_precision_with_reference_evaluator(httpx_mock):
    make_expected_requests("llm-context-precision-with-reference", httpx_mock)

    class LLMContextPrecisionWithReference(BaseRagasLLMContextPrecisionWithReference[RagasTestCase, str]):
        id = "llm-context-precision-with-reference"
        threshold = Threshold(gte=1)
        llm = evaluator_llm

        def user_input_mapper(self, test_case: RagasTestCase, output: str) -> str:
            return test_case.question

        def reference_mapper(self, test_case: RagasTestCase) -> str:
            return test_case.expected_answer

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall in Paris, France."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            LLMContextPrecisionWithReference(),
        ],
        fn=function_to_test,
    )


def test_ragas_non_llm_context_precision_with_reference_evaluator(httpx_mock):
    make_expected_requests("non-llm-context-precision-with-reference", httpx_mock)

    class NonLLMContextPrecisionWithReference(BaseRagasNonLLMContextPrecisionWithReference[RagasTestCase, str]):
        id = "non-llm-context-precision-with-reference"
        threshold = Threshold(gte=1)

        def reference_contexts_mapper(self, test_case: RagasTestCase) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall in Paris, France."]

        def retrieved_contexts_mapper(self, test_case: RagasTestCase, output: str) -> List[str]:
            return ["The Eiffel Tower stands 300 meters tall in Paris, France."]

    run_test_suite(
        id="my-test-id",
        test_cases=test_cases,
        evaluators=[
            NonLLMContextPrecisionWithReference(),
        ],
        fn=function_to_test,
    )
