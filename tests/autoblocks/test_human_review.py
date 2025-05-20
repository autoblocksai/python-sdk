from datetime import timedelta

import pytest

from autoblocks._impl.human_review.client import HumanReviewClient
from autoblocks._impl.human_review.models import ContentType
from autoblocks._impl.human_review.models import Job
from autoblocks._impl.human_review.models import JobItemDetail
from autoblocks._impl.human_review.models import JobListItem

API_KEY = "test-api-key"
APP_SLUG = "test-app"


@pytest.fixture
def client():
    return HumanReviewClient(API_KEY, APP_SLUG, timeout=timedelta(seconds=5))


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
    jobs = client.list_jobs()
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
    job = client.get_job(job_id="job-1")
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
    item = client.get_job_item(job_id="job-1", item_id="item-1")
    assert isinstance(item, JobItemDetail)
    assert item.id == "item-1"
    assert item.grades[0].score_id == "score-1"
    assert item.input_fields[0].content_type == ContentType.TEXT
    assert item.field_comments[0].field_id == "input-1"
