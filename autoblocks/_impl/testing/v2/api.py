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
from autoblocks._impl.util import ThirdPartyEnvVar
from autoblocks._impl.util import is_ci
from autoblocks._impl.util import is_cli_running
from autoblocks._impl.util import is_github_comment_disabled

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


async def send_v2_slack_notification(run_id: str, app_slug: str) -> None:
    """
    V2 Slack notification wrapper that delegates to V1 logic for maximum code reuse.
    Uses V2 app-based endpoint: /apps/{app_slug}/runs/{run_id}/slack-notification
    """
    slack_webhook_url = AutoblocksEnvVar.SLACK_WEBHOOK_URL.get()
    if is_cli_running() or not slack_webhook_url or not is_ci():
        return

    log.info(f"Sending slack notification for test run '{run_id}' in app '{app_slug}'.")
    try:
        await post_to_api(
            f"/apps/{app_slug}/runs/{run_id}/slack-notification",
            json=dict(slackWebhookUrl=slack_webhook_url),
        )
    except Exception as e:
        log.warn(f"Failed to send slack notification for test run '{run_id}' in app '{app_slug}'", exc_info=e)


async def send_v2_github_comment(app_slug: str, build_id: str) -> None:
    """
    V2 GitHub comment wrapper that delegates to V1 logic for maximum code reuse.
    Uses V2 app-based endpoint: /apps/{app_slug}/builds/{build_id}/github-comment
    """
    github_token = ThirdPartyEnvVar.GITHUB_TOKEN.get()
    if is_cli_running() or is_github_comment_disabled() or not github_token or not build_id or not is_ci():
        return

    log.info(f"Creating GitHub comment for build '{build_id}' in app '{app_slug}'.")
    try:
        async with global_state.github_comment_semaphore():
            await post_to_api(
                f"/apps/{app_slug}/builds/{build_id}/github-comment",
                json=dict(githubToken=github_token),
            )
    except Exception as e:
        log.warn(
            f"Could not create GitHub comment for build '{build_id}' in app '{app_slug}'. "
            "For more information on how to set up GitHub Actions permissions, see: "
            "https://docs.autoblocks.ai/testing/ci#git-hub-comments-github-actions-permissions",
            exc_info=e,
        )
