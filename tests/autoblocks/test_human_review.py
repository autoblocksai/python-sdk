from datetime import timedelta

import pytest

from autoblocks.api.app_client import AutoblocksAppClient
from autoblocks.human_review.models import ContentType
from autoblocks.human_review.models import Job
from autoblocks.human_review.models import JobItemDetail
from autoblocks.human_review.models import JobListItem
from autoblocks.human_review.models import JobTestCase
from autoblocks.human_review.models import OutputField
from autoblocks.human_review.models import Pair
from autoblocks.human_review.models import PairDetail
from autoblocks.human_review.models import PairItem
from autoblocks.human_review.models import TestCaseResult
from autoblocks.human_review.models import get_left_right_text
from autoblocks.human_review.models import join_output_text

API_KEY = "test-api-key"
APP_SLUG = "test-app"


@pytest.fixture
def client():
    return AutoblocksAppClient(APP_SLUG, API_KEY, timeout=timedelta(seconds=5))


def test_list_jobs(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs",
        method="GET",
        status_code=200,
        json={
            "jobs": [
                {
                    "id": "job-1",
                    "name": "Review for accuracy",
                    "reviewer": {"email": "john@example.com"},
                }
            ]
        },
    )
    jobs = client.human_review.list_jobs()
    assert len(jobs) == 1
    assert isinstance(jobs[0], JobListItem)
    assert jobs[0].id == "job-1"
    assert jobs[0].reviewer.email == "john@example.com"


def test_get_job(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1",
        method="GET",
        status_code=200,
        json={
            "id": "job-1",
            "name": "Review for accuracy",
            "reviewer": {"email": "john@example.com"},
            "scores": [
                {
                    "id": "score-1",
                    "name": "Accuracy",
                    "description": "How accurate is the output?",
                    "options": {"type": "binary"},
                }
            ],
            "items": [{"id": "item-1"}],
        },
    )
    job = client.human_review.get_job(job_id="job-1")
    assert isinstance(job, Job)
    assert job.id == "job-1"
    assert job.scores[0].options.type == "binary"
    assert job.items[0].id == "item-1"


def test_get_job_item(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1/items/item-1",
        method="GET",
        status_code=200,
        json={
            "id": "item-1",
            "grades": [
                {
                    "scoreId": "score-1",
                    "grade": 1.0,
                    "user": {"email": "john@example.com"},
                }
            ],
            "inputFields": [
                {
                    "id": "input-1",
                    "name": "input",
                    "value": "Hello, world!",
                    "contentType": "TEXT",
                }
            ],
            "outputFields": [
                {
                    "id": "output-1",
                    "name": "output",
                    "value": "Hello, world!",
                    "contentType": "TEXT",
                }
            ],
            "fieldComments": [
                {
                    "fieldId": "input-1",
                    "value": "This is a comment",
                    "startIdx": 1,
                    "endIdx": 2,
                    "inRelationToScoreName": "accuracy",
                    "user": {"email": "john@example.com"},
                }
            ],
            "inputComments": [
                {
                    "value": "This is a comment",
                    "inRelationToScoreName": "accuracy",
                    "user": {"email": "john@example.com"},
                }
            ],
            "outputComments": [
                {
                    "value": "This is a comment",
                    "inRelationToScoreName": "accuracy",
                    "user": {"email": "john@example.com"},
                }
            ],
        },
    )
    item = client.human_review.get_job_item(job_id="job-1", item_id="item-1")
    assert isinstance(item, JobItemDetail)
    assert item.id == "item-1"
    assert item.grades[0].score_id == "score-1"
    assert item.input_fields[0].content_type == ContentType.TEXT
    assert item.field_comments[0].field_id == "input-1"


def test_get_job_test_cases(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1/test_cases",
        method="GET",
        status_code=200,
        json={"testCases": [{"id": "tc-1", "input": {"prompt": "hi"}, "output": {"response": "hi"}}]},
    )

    test_cases = client.human_review.get_job_test_cases(job_id="job-1")
    assert len(test_cases) == 1
    assert isinstance(test_cases[0], JobTestCase)
    assert test_cases[0].id == "tc-1"
    assert test_cases[0].input["prompt"] == "hi"


def test_get_test_case_result(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1/test_cases/tc-1/result",
        method="GET",
        status_code=200,
        json={"id": "tc-1", "result": {"foo": "bar"}},
    )

    result = client.human_review.get_test_case_result(job_id="job-1", test_case_id="tc-1")
    assert isinstance(result, TestCaseResult)
    assert result.id == "tc-1"
    assert result.result["foo"] == "bar"


def test_list_pairs(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1/pairs",
        method="GET",
        status_code=200,
        json={
            "pairs": [
                {
                    "id": "pair-1",
                    "items": [
                        {"itemId": "b", "outputFields": [{"name": "text", "value": "B"}]},
                        {"itemId": "a", "outputFields": [{"name": "text", "value": "A"}]},
                    ],
                }
            ]
        },
    )

    pairs = client.human_review.list_pairs(job_id="job-1")
    assert len(pairs) == 1
    assert isinstance(pairs[0], Pair)
    assert {item.item_id for item in pairs[0].items} == {"a", "b"}


def test_get_pair(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/human-review/jobs/job-1/pairs/pair-1",
        method="GET",
        status_code=200,
        json={
            "id": "pair-1",
            "chosenItemId": "item-b",
            "items": [
                {
                    "itemId": "item-a",
                    "outputFields": [
                        {"name": "text", "value": "A1"},
                        {"name": "text", "value": "A2"},
                    ],
                },
                {
                    "itemId": "item-b",
                    "outputFields": [{"name": "text", "value": "B"}],
                },
            ],
        },
    )

    pair = client.human_review.get_pair(job_id="job-1", pair_id="pair-1")
    assert isinstance(pair, PairDetail)
    assert pair.id == "pair-1"
    assert pair.chosen_item_id == "item-b"
    texts = [join_output_text(item) for item in pair.items]
    assert "A1\nA2" in texts


def test_left_right_helper_sorts_by_item_id():
    pair = Pair(
        id="p1",
        items=[
            PairItem(item_id="b", output_fields=[OutputField(name="text", value="B")]),  # type: ignore[call-arg]
            PairItem(item_id="a", output_fields=[OutputField(name="text", value="A")]),  # type: ignore[call-arg]
        ],
    )
    left_text, right_text = get_left_right_text(pair)
    assert left_text == "A"
    assert right_text == "B"
