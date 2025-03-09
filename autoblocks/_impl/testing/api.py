import dataclasses
import logging
import os
import traceback
from typing import Any
from typing import Optional
from typing import Sequence

from httpx import Response
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.context_vars import get_revision_usage
from autoblocks._impl.testing.models import Evaluation
from autoblocks._impl.testing.models import TestCaseContext
from autoblocks._impl.testing.models import TestCaseType
from autoblocks._impl.testing.util import GridSearchParams
from autoblocks._impl.testing.util import GridSearchParamsCombo
from autoblocks._impl.testing.util import serialize_output
from autoblocks._impl.testing.util import serialize_output_for_human_review
from autoblocks._impl.testing.util import serialize_test_case
from autoblocks._impl.testing.util import serialize_test_case_for_human_review
from autoblocks._impl.tracer.tracer import test_events
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import ThirdPartyEnvVar
from autoblocks._impl.util import all_settled
from autoblocks._impl.util import is_ci
from autoblocks._impl.util import is_cli_running
from autoblocks._impl.util import is_github_comment_disabled

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=30), reraise=True)
async def post_to_cli_with_retry(
    url: str,
    json: dict[str, Any],
) -> Response:
    resp = await global_state.http_client().post(
        url,
        json=json,
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp


async def post_to_cli(
    path: str,
    json: dict[str, Any],
) -> Response:
    cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
    # We check this ahead of time, so it should always be set here
    if not cli_server_address:
        raise Exception("CLI server address is not set.")

    async with global_state.test_run_api_semaphore():
        return await post_to_cli_with_retry(
            f"{cli_server_address}{path}",
            json,
        )


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
    resp.raise_for_status()
    return resp


async def post_to_api(
    path: str,
    json: dict[str, Any],
) -> Response:
    sub_path = "/testing/ci" if is_ci() else "/testing/local"
    api_key = AutoblocksEnvVar.API_KEY.get()
    if not api_key:
        raise ValueError(f"You must set the {AutoblocksEnvVar.API_KEY} environment variable.")

    async with global_state.test_run_api_semaphore():
        return await post_to_api_with_retry(
            f"{API_ENDPOINT}{sub_path}{path}",
            api_key,
            json,
        )


async def send_info_for_alignment_mode(
    test_id: str,
    test_cases: Sequence[TestCaseType],
    caller_filepath: Optional[str],
) -> None:
    """
    Notifies the CLI with metadata about this test suite when running in "alignment mode",
    i.e. npx autoblocks testing align -- <cmd>
    """
    # Double check this is the correct test suite
    assert AutoblocksEnvVar.ALIGN_TEST_EXTERNAL_ID.get() == test_id

    # Tells the CLI what it needs to know about this test suite
    await post_to_cli(
        "/info",
        json=dict(
            language="python",
            runTestSuiteCalledFromDirectory=os.path.dirname(caller_filepath) if caller_filepath else None,
            testCaseHashes=[test_case.hash() for test_case in test_cases],
        ),
    )


async def send_error(
    test_id: str, run_id: Optional[str], test_case_hash: Optional[str], evaluator_id: Optional[str], error: Exception
) -> None:
    if is_cli_running():
        try:
            await post_to_cli(
                "/errors",
                json=dict(
                    testExternalId=test_id,
                    runId=run_id,
                    testCaseHash=test_case_hash,
                    evaluatorExternalId=evaluator_id,
                    error=dict(
                        name=type(error).__name__,
                        message=str(error),
                        stacktrace=traceback.format_exc(),
                    ),
                ),
            )
        except Exception:
            log.exception(f"Error in test '{test_id}'", exc_info=error)
    else:
        log.exception(f"Error in test '{test_id}'", exc_info=error)


async def send_start_grid_search_run(
    grid_search_params: GridSearchParams,
) -> str:
    if is_cli_running():
        grid_resp = await post_to_cli(
            "/grids",
            json=dict(gridSearchParams=grid_search_params),
        )
    else:
        grid_resp = await post_to_api(
            "/grids",
            json=dict(gridSearchParams=grid_search_params),
        )

    return grid_resp.json()["id"]  # type: ignore [no-any-return]


async def send_start_test_run(
    test_external_id: str,
    message: Optional[str],
    grid_search_run_group_id: Optional[str],
    grid_search_params_combo: Optional[GridSearchParamsCombo],
) -> str:
    if is_cli_running():
        start_resp = await post_to_cli(
            "/start",
            json=dict(
                testExternalId=test_external_id,
                gridSearchRunGroupId=grid_search_run_group_id,
                gridSearchParamsCombo=grid_search_params_combo,
            ),
        )
    else:
        start_resp = await post_to_api(
            "/runs",
            json=dict(
                testExternalId=test_external_id,
                message=message,
                buildId=AutoblocksEnvVar.CI_TEST_RUN_BUILD_ID.get(),
                gridSearchRunGroupId=grid_search_run_group_id,
                gridSearchParamsCombo=grid_search_params_combo,
            ),
        )

    return start_resp.json()["id"]  # type: ignore [no-any-return]


async def send_test_events(
    run_id: str,
    test_case_hash: str,
    test_case_result_id: str,
) -> None:
    try:
        if (run_id, test_case_hash) not in test_events:
            return
        # If the key exists, it means there are events to send
        events = test_events[(run_id, test_case_hash)]
        await post_to_api(
            f"/runs/{run_id}/results/{test_case_result_id}/events",
            json=dict(testCaseEvents=[event.to_json() for event in events]),
        )
        # Remove the events from the test_events dict after they have been sent
        del test_events[(run_id, test_case_hash)]
    except Exception as e:
        log.warn(f"Failed to send test events for run '{run_id}' and test case hash '{test_case_hash}'", exc_info=e)


async def send_test_case_result(
    test_external_id: str,
    run_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: Any,
    test_case_duration_ms: Optional[float] = None,
) -> str:
    # Revision usage is collected throughout a test case's run
    revision_usage = get_revision_usage()
    dataset_item_id = test_case_ctx.test_case.serialize_dataset_item_id()
    serialized_test_case = serialize_test_case(test_case_ctx.test_case)
    serialized_output = serialize_output(output)
    test_case_revision_usage = [usage.serialize() for usage in revision_usage] if revision_usage else None
    serialized_test_case_human_review_input_fields = serialize_test_case_for_human_review(test_case_ctx.test_case)
    serialized_test_case_human_review_output_fields = serialize_output_for_human_review(output)
    if is_cli_running():
        results_resp = await post_to_cli(
            "/results",
            json=dict(
                testExternalId=test_external_id,
                runId=run_id,
                testCaseHash=test_case_ctx.hash(),
                datasetItemId=dataset_item_id,
                testCaseBody=serialized_test_case,
                testCaseOutput=serialized_output,
                testCaseDurationMs=test_case_duration_ms,
                testCaseRevisionUsage=test_case_revision_usage,
                testCaseHumanReviewInputFields=serialized_test_case_human_review_input_fields,
                testCaseHumanReviewOutputFields=serialized_test_case_human_review_output_fields,
            ),
        )
        result_id_cli: str = results_resp.json()["id"]
        await send_test_events(run_id, test_case_ctx.hash(), result_id_cli)
        return result_id_cli
    else:
        # results to the public api are split into multiple requests to avoid errors when sending large amounts of data
        # the CLI splits the results into the same way
        results_resp = await post_to_api(
            f"/runs/{run_id}/results",
            json=dict(
                testCaseHash=test_case_ctx.hash(),
                datasetItemId=dataset_item_id,
                testCaseDurationMs=test_case_duration_ms,
                testCaseRevisionUsage=test_case_revision_usage,
            ),
        )
        result_id: str = results_resp.json()["id"]
        results = await all_settled(
            [
                post_to_api(
                    f"/runs/{run_id}/results/{result_id}/body",
                    json=dict(
                        testCaseBody=serialized_test_case,
                    ),
                ),
                post_to_api(
                    f"/runs/{run_id}/results/{result_id}/output",
                    json=dict(
                        testCaseOutput=serialized_output,
                    ),
                ),
                send_test_events(run_id, test_case_ctx.hash(), result_id),
            ]
        )
        for result in results:
            if isinstance(result, Exception):
                log.warn(
                    "Failed to send part of the test case results to Autoblocks\n"
                    f"test case hash: {test_case_ctx.hash()}\n"
                    f"{result}",
                    exc_info=result,
                )

        try:
            await post_to_api(
                f"/runs/{run_id}/results/{result_id}/human-review-fields",
                json=dict(
                    testCaseHumanReviewInputFields=serialized_test_case_human_review_input_fields,
                    testCaseHumanReviewOutputFields=serialized_test_case_human_review_output_fields,
                ),
            )
        except Exception as e:
            log.warn(
                "Failed to send human review fields to Autoblocks\n" f"test case hash: {test_case_ctx.hash()}\n",
                exc_info=e,
            )

        try:
            await post_to_api(f"/runs/{run_id}/results/{result_id}/ui-based-evaluations", json={})
        except Exception as e:
            log.warn("Failed to run ui based evaluations\n" f"test case hash: {test_case_ctx.hash()}\n", exc_info=e)

        return result_id


async def send_eval(
    test_external_id: str,
    run_id: str,
    test_case_hash: str,
    evaluator_external_id: str,
    evaluation: Evaluation,
    test_case_result_id: str,
) -> None:
    # Revision usage is collected throughout an evaluator's evaluate_test_case call on a test case
    revision_usage = get_revision_usage()
    eval_revision_usage = [usage.serialize() for usage in revision_usage] if revision_usage else None
    threshold = dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None
    assertions = [assertion.serialize() for assertion in evaluation.assertions] if evaluation.assertions else None
    if is_cli_running():
        await post_to_cli(
            "/evals",
            json=dict(
                testExternalId=test_external_id,
                runId=run_id,
                testCaseHash=test_case_hash,
                evaluatorExternalId=evaluator_external_id,
                score=evaluation.score,
                threshold=threshold,
                metadata=evaluation.metadata,
                revisionUsage=eval_revision_usage,
                assertions=assertions,
            ),
        )
    else:
        await post_to_api(
            f"/runs/{run_id}/results/{test_case_result_id}/evaluations",
            json=dict(
                evaluatorExternalId=evaluator_external_id,
                score=evaluation.score,
                passed=evaluation.passed(),
                threshold=threshold,
                metadata=evaluation.metadata,
                revisionUsage=eval_revision_usage,
                assertions=assertions,
            ),
        )


async def send_end_test_run(
    test_external_id: str,
    run_id: str,
) -> None:
    if is_cli_running():
        await post_to_cli(
            "/end",
            json=dict(testExternalId=test_external_id, runId=run_id),
        )
    else:
        await post_to_api(f"/runs/{run_id}/end", json={})


async def send_slack_notification(
    run_id: str,
) -> None:
    slack_webhook_url = AutoblocksEnvVar.SLACK_WEBHOOK_URL.get()
    if is_cli_running() or not slack_webhook_url or not is_ci():
        return

    log.info(f"Sending slack notification for test run '{run_id}'.")
    try:
        await post_to_api(
            f"/runs/{run_id}/slack-notification",
            json=dict(slackWebhookUrl=slack_webhook_url),
        )
    except Exception as e:
        log.warn(f"Failed to send slack notification for test run '{run_id}'", exc_info=e)


async def send_github_comment() -> None:
    github_token = ThirdPartyEnvVar.GITHUB_TOKEN.get()
    build_id = AutoblocksEnvVar.CI_TEST_RUN_BUILD_ID.get()
    if is_cli_running() or is_github_comment_disabled() or not github_token or not build_id or not is_ci():
        return

    log.info(f"Creating GitHub comment for build '{build_id}'.")
    try:
        async with global_state.github_comment_semaphore():
            await post_to_api(
                f"/builds/{build_id}/github-comment",
                json=dict(githubToken=github_token),
            )
    except Exception as e:
        log.warn(
            "Could not create GitHub comment for build '{build_id}'."
            "For more information on how to set up GitHub Actions permissions, see: "
            "https://docs.autoblocks.ai/testing/ci#git-hub-comments-github-actions-permissions",
            exc_info=e,
        )


async def send_create_human_review_job(run_id: str, assignee_email_address: str, name: str) -> None:
    await post_to_api(
        f"/runs/{run_id}/human-review-job", json=dict(assigneeEmailAddress=assignee_email_address, name=name)
    )
