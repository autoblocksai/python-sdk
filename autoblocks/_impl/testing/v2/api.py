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


async def send_v2_slack_notification(
    run_id: str,
    app_slug: str,
    build_id: str,
    use_simple_format: bool = False,
) -> None:
    """
    Send Slack notification via V2 testing route:
      POST /testing/runs/{run_id}/slack-notification?buildId=...&useSimpleFormat=true|false
      Body: { webhookUrl, appSlug }
    """
    slack_webhook_url = AutoblocksEnvVar.SLACK_WEBHOOK_URL.get()
    if not slack_webhook_url or not is_ci():
        return

    log.info(f"Sending slack notification for test run '{run_id}' in app '{app_slug}'.")
    try:
        query = f"buildId={build_id}"
        if use_simple_format:
            query = f"{query}&useSimpleFormat=true"

        await post_to_api(
            f"/testing/runs/{run_id}/slack-notification?{query}",
            json=dict(webhookUrl=slack_webhook_url, appSlug=app_slug),
        )
    except Exception as e:
        log.warning(
            f"Failed to send slack notification for test run '{run_id}' in app '{app_slug}'",
            exc_info=e,
        )


async def send_v2_github_comment(run_id: str, app_slug: str, build_id: str) -> None:
    """
    Send GitHub PR comment via V2 testing route:
      POST /testing/runs/{run_id}/github-comment?buildId=...
      Body: { githubToken, appSlug }
    """
    github_token = ThirdPartyEnvVar.GITHUB_TOKEN.get()
    if is_github_comment_disabled() or not github_token or not build_id or not is_ci():
        return

    log.info(f"Creating GitHub comment for build '{build_id}' in app '{app_slug}'.")
    try:
        async with global_state.github_comment_semaphore():
            await post_to_api(
                f"/testing/runs/{run_id}/github-comment?buildId={build_id}",
                json=dict(githubToken=github_token, appSlug=app_slug),
            )
    except Exception as e:
        log.warning(
            f"Could not create GitHub comment for build '{build_id}' in app '{app_slug}'. "
            "For more information on how to set up GitHub Actions permissions, see: "
            "https://docs.autoblocks.ai/testing/ci#git-hub-comments-github-actions-permissions",
            exc_info=e,
        )


async def send_create_result(
    *,
    app_slug: str,
    run_id: str,
    environment: str,
    started_at: str,
    duration_ms: float,
    status: str,
    input_raw: str,
    output_raw: str,
    input_map: dict[str, str],
    output_map: dict[str, str],
    evaluator_id_to_result: dict[str, bool],
    evaluator_id_to_reason: dict[str, str],
    evaluator_id_to_score: dict[str, float],
    run_message: Optional[str] = None,
) -> Response:
    return await post_to_api(
        "/testing/results",
        json=dict(
            appSlug=app_slug,
            runId=run_id,
            environment=environment,
            runMessage=run_message,
            startedAt=started_at,
            durationMS=int(round(duration_ms)),
            status=status,
            inputRaw=input_raw,
            outputRaw=output_raw,
            input=input_map,
            output=output_map,
            evaluatorIdToResult=evaluator_id_to_result,
            evaluatorIdToReason=evaluator_id_to_reason,
            evaluatorIdToScore=evaluator_id_to_score,
        ),
    )
