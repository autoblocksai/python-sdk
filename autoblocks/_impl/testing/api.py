import dataclasses
import logging
import os
import traceback
from typing import Any
from typing import Optional
from typing import Sequence

from httpx import Response

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
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import all_settled
from autoblocks._impl.util import is_cli_running
from autoblocks.tracer import flush

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


async def post_to_cli(
    path: str,
    json: dict[str, Any],
) -> Optional[Response]:
    cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
    if not cli_server_address:
        raise Exception("CLI server address is not set.")

    return await global_state.http_client().post(
        f"{cli_server_address}{path}",
        json=json,
        timeout=TIMEOUT_SECONDS,  # seconds
    )


async def post_to_api(
    path: str,
    json: dict[str, Any],
) -> Optional[Response]:
    sub_path = "/testing/local"
    api_key = AutoblocksEnvVar.API_KEY.get()
    if not api_key:
        raise ValueError(f"You must set the {AutoblocksEnvVar.API_KEY} environment variable.")
    return await global_state.http_client().post(
        f"{API_ENDPOINT}{sub_path}{path}",
        json=json,
        timeout=TIMEOUT_SECONDS,  # seconds,
        headers={"Authorization": f"Bearer {api_key}"},
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
    else:
        log.error(str(error))


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

    if not grid_resp:
        raise Exception("Failed to start grid search run.")

    grid_resp.raise_for_status()
    return grid_resp.json()["id"]  # type: ignore [no-any-return]


async def send_start_test_run(
    test_external_id: str,
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
                message=None,
                # TODO: Handle CI runs when not using CLI
                buildId=None,
                gridSearchRunGroupId=grid_search_run_group_id,
                gridSearchParamsCombo=grid_search_params_combo,
            ),
        )

    if not start_resp:
        raise Exception(f"Failed to start test run for {test_external_id}.")
    start_resp.raise_for_status()
    return start_resp.json()["id"]  # type: ignore [no-any-return]


async def send_test_case_result(
    test_external_id: str,
    run_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: Any,
    test_case_duration_ms: float,
) -> str:
    # Revision usage is collected throughout a test case's run
    revision_usage = get_revision_usage()

    # Flush the logs before we send the result, since the CLI
    # accumulates the events and sends them as a batch along
    # with the result.
    flush()

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
                testCaseBody=serialized_test_case,
                testCaseOutput=serialized_output,
                testCaseDurationMs=test_case_duration_ms,
                testCaseRevisionUsage=test_case_revision_usage,
                testCaseHumanReviewInputFields=serialized_test_case_human_review_input_fields,
                testCaseHumanReviewOutputFields=serialized_test_case_human_review_output_fields,
            ),
        )
        if not results_resp:
            raise Exception(f"Failed to send test case result for {test_external_id}.")
        results_resp.raise_for_status()
        return results_resp.json()["id"]  # type: ignore [no-any-return]
    else:
        # results to the public api are split into multiple requests to avoid errors when sending large amounts of data
        # the CLI splits the results into the same way
        results_resp = await post_to_api(
            f"/runs/{run_id}/results",
            json=dict(
                testCaseHash=test_case_ctx.hash(),
                testCaseDurationMs=test_case_duration_ms,
                testCaseRevisionUsage=test_case_revision_usage,
            ),
        )
        if not results_resp:
            raise Exception(f"Failed to send test case result for {test_external_id}.")
        results_resp.raise_for_status()
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
            ]
        )
        for result in results:
            if isinstance(result, Exception):
                log.warn(
                    "Failed to send part of the test case results to Autoblocks\n"
                    f"test case hash: {test_case_ctx.hash()}\n"
                    f"{result}"
                )

        human_review_results_resp = await post_to_api(
            f"/runs/{run_id}/results/{result_id}/human-review-fields",
            json=dict(
                testCaseHumanReviewInputFields=serialized_test_case_human_review_input_fields,
                testCaseHumanReviewOutputFields=serialized_test_case_human_review_output_fields,
            ),
        )
        try:
            if not human_review_results_resp:
                raise Exception(f"Failed to send human review fields to Autoblocks for {test_external_id}.")
            human_review_results_resp.raise_for_status()
        except Exception as e:
            log.warn(
                "Failed to send human review fields to Autoblocks\n" f"test case hash: {test_case_ctx.hash()}\n" f"{e}"
            )

        await post_to_api(f"/runs/{run_id}/results/{result_id}/ui-based-evaluations", json={})
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
            ),
        )
    else:
        resp = await post_to_api(
            f"/runs/{run_id}/results/{test_case_result_id}/evaluations",
            json=dict(
                evaluatorExternalId=evaluator_external_id,
                score=evaluation.score,
                passed=evaluation.passed(),
                threshold=threshold,
                metadata=evaluation.metadata,
                revisionUsage=eval_revision_usage,
            ),
        )
        if resp:
            resp.raise_for_status()
        else:
            raise Exception(f"Failed to send evaluation to Autoblocks for {test_external_id}.")


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
