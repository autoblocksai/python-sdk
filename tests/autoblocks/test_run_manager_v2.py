import json
import os
from dataclasses import dataclass
from typing import Any
from typing import List
from typing import Optional
from unittest import mock

import pytest

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.testing.models import BaseTestCase
from autoblocks._impl.testing.models import BaseTestEvaluator
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import HumanReviewField
from autoblocks._impl.testing.models import HumanReviewFieldContentType
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.v2.run_manager import RunManager
from autoblocks._impl.util import AutoblocksEnvVar
from tests.util import ANY_STRING


@pytest.fixture(autouse=True)
def mock_env_var():
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.V2_API_KEY.value: "mock-api-key",
            "CI": "false",
        },
    ):
        yield


@dataclass
class MyTestCase(BaseTestCase):
    input: str

    def hash(self) -> str:
        return self.input

    def serialize_for_human_review(self) -> List[HumanReviewField]:
        return [HumanReviewField(name="input", value=self.input, content_type=HumanReviewFieldContentType.TEXT)]


@dataclass
class MyOutput:
    output: str

    def serialize_for_human_review(self) -> List[HumanReviewField]:
        return [HumanReviewField(name="output", value=self.output, content_type=HumanReviewFieldContentType.TEXT)]


class MyEvaluator(BaseTestEvaluator):
    @property
    def id(self) -> str:
        return "evaluator-external-id"

    def evaluate_test_case(self, *args: Any, **kwargs: Any) -> Optional[Evaluation]:
        return Evaluation(score=1, threshold=Threshold(gte=0.5), metadata={"reason": "ok"})


def test_does_not_allow_adding_result_after_run_has_ended_v2():
    test_run = RunManager(app_slug="my-app", run_message="Test run")

    test_run.start()
    test_run.end()

    with pytest.raises(ValueError):
        test_run.add_result(
            test_case=MyTestCase(input="test"),
            output=MyOutput(output="test"),
            duration_ms=100,
        )


def test_full_lifecycle_v2(httpx_mock):
    # Expect composite result POST
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/testing/results",
        method="POST",
        match_json=dict(
            appSlug="my-app",
            runId=ANY_STRING,
            environment="test",
            runMessage="Test run",
            startedAt="2025-01-01T00:00:00.000Z",
            durationMS=100,
            status="SUCCESS",
            inputRaw=json.dumps({"input": "test"}),
            outputRaw=json.dumps({"output": "test"}),
            input={"input": "test"},
            output={"output": "test"},
            evaluatorIdToResult={"evaluator-external-id": True},
            evaluatorIdToReason={"evaluator-external-id": "ok"},
            evaluatorIdToScore={"evaluator-external-id": 1},
        ),
        json=dict(executionId="mock-exec-id"),
    )

    # Expect HR job POST
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/my-app/human-review/jobs",
        method="POST",
        match_json=dict(
            runId=ANY_STRING,
            startTimestamp=ANY_STRING,
            endTimestamp=ANY_STRING,
            rubricId=None,
            assigneeEmailAddresses=["test@test.com"],
            name="Test human review job",
        ),
        json=dict(),
    )

    test_run = RunManager(app_slug="my-app", run_message="Test run")

    test_run.start()
    exec_id = test_run.add_result(
        test_case=MyTestCase(input="test"),
        output=MyOutput(output="test"),
        duration_ms=100,
        evaluators=[MyEvaluator()],
        started_at="2025-01-01T00:00:00.000Z",
    )
    assert exec_id == "mock-exec-id"

    test_run.end()
    test_run.create_human_review(
        name="Test human review job",
        assignee_email_addresses=["test@test.com"],
    )


def test_end_without_start_sets_timestamps_and_allows_human_review(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/apps/my-app/human-review/jobs",
        method="POST",
        match_json=dict(
            runId=ANY_STRING,
            startTimestamp=ANY_STRING,
            endTimestamp=ANY_STRING,
            rubricId=None,
            assigneeEmailAddresses=["a@test.com"],
            name="HR job",
        ),
        json=dict(),
    )

    test_run = RunManager(app_slug="my-app")

    # end() should backfill start timestamp and allow HR creation
    test_run.end()
    assert test_run.can_create_human_review is True
    assert test_run.started_at is not None
    assert test_run.ended_at is not None

    test_run.create_human_review(
        name="HR job",
        assignee_email_addresses=["a@test.com"],
    )


def test_add_result_without_evaluators_sends_empty_maps(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT_V2}/testing/results",
        method="POST",
        match_json=dict(
            appSlug="my-app",
            runId=ANY_STRING,
            environment="test",
            runMessage=None,
            startedAt=ANY_STRING,
            durationMS=250,
            status="SUCCESS",
            inputRaw=json.dumps({"input": "test"}),
            outputRaw=json.dumps({"output": "test"}),
            input={"input": "test"},
            output={"output": "test"},
            evaluatorIdToResult={},
            evaluatorIdToReason={},
            evaluatorIdToScore={},
        ),
        json=dict(executionId="exec-1"),
    )

    test_run = RunManager(app_slug="my-app")
    test_run.start()
    exec_id = test_run.add_result(
        test_case=MyTestCase(input="test"),
        output=MyOutput(output="test"),
        duration_ms=250,
    )
    assert exec_id == "exec-1"
