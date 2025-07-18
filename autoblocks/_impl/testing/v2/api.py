import logging
from typing import Any
from typing import List
from typing import Optional

from httpx import Response
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.util import AutoblocksEnvVar

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=30), reraise=True)
async def post_to_api_with_retry(
    url: str,
    api_key: str,
    json: dict[str, Any],
) -> Response:
    resp = await global_state.http_client().post(
        url,
        json=json,
        timeout=TIMEOUT_SECONDS,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if not resp.is_success:
        try:
            error_body = resp.text
            log.error(f"API request failed with status {resp.status_code} for {url}. Response body: {error_body}")
        except Exception:
            log.error(f"API request failed with status {resp.status_code} for {url}. Could not read response body.")

    resp.raise_for_status()
    return resp


async def post_to_api(
    path: str,
    json: dict[str, Any],
) -> Response:
    api_key = AutoblocksEnvVar.V2_API_KEY.get()
    if not api_key:
        raise ValueError(f"You must set the {AutoblocksEnvVar.V2_API_KEY} environment variable.")

    url = f"{API_ENDPOINT_V2}{path}"
    async with global_state.test_run_api_semaphore():
        return await post_to_api_with_retry(
            url,
            api_key,
            json,
        )


async def send_create_human_review_job(
    run_id: str,
    start_timestamp: str,
    end_timestamp: str,
    assignee_email_addresses: List[str],
    name: str,
    app_slug: str,
    rubric_id: Optional[str] = None,
) -> None:

    await post_to_api(
        f"/apps/{app_slug}/human-review/jobs",
        json=dict(
            runId=run_id,
            startTimestamp=start_timestamp,
            endTimestamp=end_timestamp,
            rubricId=rubric_id,
            assigneeEmailAddresses=assignee_email_addresses,
            name=name,
        ),
    )
