"""Human Review API Client."""

import logging
from datetime import timedelta
from typing import List

from autoblocks._impl.api.base_app_resource_client import BaseAppResourceClient
from autoblocks._impl.api.exceptions import ValidationError
from autoblocks._impl.api.utils.serialization import deserialize_model
from autoblocks._impl.human_review.models import Job
from autoblocks._impl.human_review.models import JobItemDetail
from autoblocks._impl.human_review.models import JobListItem
from autoblocks._impl.human_review.models import JobPair
from autoblocks._impl.human_review.models import JobPairsResponse
from autoblocks._impl.human_review.models import JobsResponse
from autoblocks._impl.human_review.models import JobTestCase
from autoblocks._impl.human_review.models import JobTestCaseResult
from autoblocks._impl.human_review.models import JobTestCasesResponse

log = logging.getLogger(__name__)


class HumanReviewClient(BaseAppResourceClient):
    """Human Review API Client"""

    def __init__(self, api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> None:
        super().__init__(api_key, app_slug, timeout)

    def list_jobs(self) -> List[JobListItem]:
        """
        List all human review jobs in the app.

        Returns:
            List of human review jobs
        """
        path = self._build_app_path("human-review", "jobs")
        response = self._make_request("GET", path)
        jobs_response = deserialize_model(JobsResponse, response)
        return jobs_response.jobs

    def get_job(self, *, job_id: str) -> Job:
        """
        Get a specific human review job by ID.

        Args:
            job_id: Job ID (required)

        Returns:
            Job details

        Raises:
            ValidationError: If job_id is not provided
        """
        if not job_id:
            raise ValidationError("Job ID is required")

        path = self._build_app_path("human-review", "jobs", job_id)
        response = self._make_request("GET", path)
        return deserialize_model(Job, response)

    def get_job_item(self, *, job_id: str, item_id: str) -> JobItemDetail:
        """
        Get a specific job item by ID.

        Args:
            job_id: Job ID (required)
            item_id: Item ID (required)

        Returns:
            Job item details

        Raises:
            ValidationError: If job_id or item_id are not provided
        """
        if not job_id:
            raise ValidationError("Job ID is required")
        if not item_id:
            raise ValidationError("Item ID is required")

        path = self._build_app_path("human-review", "jobs", job_id, "items", item_id)
        response = self._make_request("GET", path)
        return deserialize_model(JobItemDetail, response)

    def get_job_test_cases(self, *, job_id: str) -> List[JobTestCase]:
        """List all test cases for a job."""

        if not job_id:
            raise ValidationError("Job ID is required")

        path = self._build_app_path("human-review", "jobs", job_id, "test_cases")
        response = self._make_request("GET", path)
        test_cases_response = deserialize_model(JobTestCasesResponse, response)
        return test_cases_response.test_cases

    def get_job_test_case_result(self, *, job_id: str, test_case_id: str) -> JobTestCaseResult:
        """Get result for a specific test case."""

        if not job_id:
            raise ValidationError("Job ID is required")
        if not test_case_id:
            raise ValidationError("Test case ID is required")

        path = self._build_app_path(
            "human-review",
            "jobs",
            job_id,
            "test_cases",
            test_case_id,
            "result",
        )
        response = self._make_request("GET", path)
        return deserialize_model(JobTestCaseResult, response)

    def get_job_pairs(self, *, job_id: str) -> List[JobPair]:
        """List all comparison pairs for a job."""

        if not job_id:
            raise ValidationError("Job ID is required")

        path = self._build_app_path("human-review", "jobs", job_id, "pairs")
        response = self._make_request("GET", path)
        pairs_response = deserialize_model(JobPairsResponse, response)
        return pairs_response.pairs

    def get_job_pair(self, *, job_id: str, pair_id: str) -> JobPair:
        """Get a specific comparison pair."""

        if not job_id:
            raise ValidationError("Job ID is required")
        if not pair_id:
            raise ValidationError("Pair ID is required")

        path = self._build_app_path("human-review", "jobs", job_id, "pairs", pair_id)
        response = self._make_request("GET", path)
        return deserialize_model(JobPair, response)


def create_human_review_client(
    api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)
) -> HumanReviewClient:
    """
    Create a HumanReviewClient instance.

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout: Request timeout as timedelta (default: 60 seconds)

    Returns:
        HumanReviewClient instance
    """
    return HumanReviewClient(api_key=api_key, app_slug=app_slug, timeout=timeout)
