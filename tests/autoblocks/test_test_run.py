import os
import uuid
from dataclasses import dataclass
from typing import List
from unittest import mock

import pytest

from autoblocks._impl.testing.models import EvaluationWithId
from autoblocks._impl.testing.models import HumanReviewField
from autoblocks._impl.testing.models import HumanReviewFieldContentType
from autoblocks._impl.testing.models import Threshold
from autoblocks._impl.testing.test_run import TestRun
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.testing.models import BaseTestCase
from tests.util import expect_api_post_request


@pytest.fixture(autouse=True)
def mock_env_var():
    with mock.patch.dict(
        os.environ,
        {
            AutoblocksEnvVar.API_KEY.value: "mock-api-key",
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
        return [
            HumanReviewField(
                name="input",
                value=self.input,
                content_type=HumanReviewFieldContentType.TEXT,
            )
        ]


@dataclass
class MyOutput:
    output: str

    def serialize_for_human_review(self) -> List[HumanReviewField]:
        return [
            HumanReviewField(
                name="output",
                value=self.output,
                content_type=HumanReviewFieldContentType.TEXT,
            )
        ]


def test_does_not_allow_adding_result_before_starting():
    test_run = TestRun[MyTestCase, MyOutput]("test-id", "Test run")

    with pytest.raises(ValueError):
        test_run.add_result(
            test_case=MyTestCase(input="test"),
            output=MyOutput(output="test"),
            test_case_duration_ms=100,
            evaluations=[
                EvaluationWithId(
                    id="evaluator-external-id",
                    score=1,
                    threshold=Threshold(gte=0.5),
                )
            ],
        )


def test_does_not_allow_adding_result_after_run_has_ended(httpx_mock):
    test_run = TestRun[MyTestCase, MyOutput]("test-id", "Test run")
    mock_run_id = str(uuid.uuid4())

    expect_api_post_request(
        httpx_mock,
        path="/testing/local/runs",
        body=dict(
            testExternalId="test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
            message="Test run",
            buildId=None,
        ),
        json=dict(id=mock_run_id),
    )
    expect_api_post_request(httpx_mock, path=f"/testing/local/runs/{mock_run_id}/end", body=dict())

    test_run.start()
    test_run.end()

    with pytest.raises(ValueError):
        test_run.add_result(
            test_case=MyTestCase(input="test"),
            output=MyOutput(output="test"),
            test_case_duration_ms=100,
            evaluations=[
                EvaluationWithId(
                    id="evaluator-external-id",
                    score=1,
                    threshold=Threshold(gte=0.5),
                )
            ],
        )


def test_does_not_allow_ending_run_that_has_not_been_started():
    test_run = TestRun[MyTestCase, MyOutput]("test-id", "Test run")

    with pytest.raises(ValueError):
        test_run.end()


async def test_full_lifecycle(httpx_mock):
    mock_run_id = str(uuid.uuid4())
    mock_test_case_result_id = str(uuid.uuid4())

    expect_api_post_request(
        httpx_mock,
        path="/testing/local/runs",
        body=dict(
            testExternalId="test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
            message="Test run",
            buildId=None,
        ),
        json=dict(id=mock_run_id),
    )

    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/results",
        body=dict(
            testExternalId="test-id",
            runId=mock_run_id,
            testCaseHash="test",
            testCaseBody=dict(input="test"),
            testCaseOutput=dict(output="test"),
            testCaseDurationMs=100,
            testCaseRevisionUsage=None,
            testCaseHumanReviewInputFields=[
                dict(name="input", value="test", contentType="text"),
            ],
            testCaseHumanReviewOutputFields=[
                dict(name="output", value="test", contentType="text"),
            ],
        ),
        json=dict(id=mock_test_case_result_id),
    )

    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/results/{mock_test_case_result_id}/evaluations",
        body=dict(
            testExternalId="test-id",
            runId=mock_run_id,
            testCaseHash="test",
            evaluatorExternalId="evaluator-external-id",
            score=1,
            threshold=dict(lt=None, lte=None, gt=None, gte=0.5),
            metadata=None,
            revisionUsage=None,
            assertions=None,
        ),
    )

    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/end",
        body=dict(),
    )

    expect_api_post_request(
        httpx_mock,
        path=f"/testing/local/runs/{mock_run_id}/human-review-jobs",
        body=dict(
            runId=mock_run_id,
            assigneeEmailAddress="test@test.com",
            name="Test human review job",
        ),
    )

    test_run = TestRun[MyTestCase, MyOutput]("test-id", "Test run")

    test_run.start()
    assert test_run.run_id == mock_run_id

    test_run.add_result(
        test_case=MyTestCase(input="test"),
        output=MyOutput(output="test"),
        test_case_duration_ms=100,
        evaluations=[
            EvaluationWithId(
                id="evaluator-external-id",
                score=1,
                threshold=Threshold(gte=0.5),
            )
        ],
    )

    test_run.end()

    test_run.create_human_review_job(
        assignee_email_address="test@test.com",
        name="Test human review job",
    )

    # Verify all expected requests were made
    requests = httpx_mock.get_requests()
    assert len(requests) == 5


async def test_create_human_review_job_before_start():
    test_run = TestRun[MyTestCase, MyOutput]("test-id", "Test run")

    with pytest.raises(ValueError):
        test_run.create_human_review_job(
            assignee_email_address="test@test.com",
            name="Test human review job",
        )
