import dataclasses
import logging
import os
import traceback
from typing import Any
from typing import Optional
from typing import Sequence

from httpx import HTTPStatusError
from httpx import Response

from autoblocks._impl import global_state
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
from autoblocks.tracer import flush

log = logging.getLogger(__name__)


async def post_to_cli(
    path: str,
    json: dict[str, Any],
) -> Optional[Response]:
    cli_server_address = AutoblocksEnvVar.CLI_SERVER_ADDRESS.get()
    if cli_server_address:
        return await global_state.http_client().post(
            f"{cli_server_address}{path}",
            json=json,
            timeout=30,  # seconds
        )

    # If the CLI server address is not set then the tests are being run
    # directly. In this case we just log the request that would have been
    # sent to the CLI.
    log.debug(f"{path}: {json}")
    return None


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


async def send_eval(
    test_external_id: str,
    run_id: str,
    test_case_hash: str,
    evaluator_external_id: str,
    evaluation: Evaluation,
) -> None:
    # Revision usage is collected throughout an evaluator's evaluate_test_case call on a test case
    revision_usage = get_revision_usage()

    await post_to_cli(
        "/evals",
        json=dict(
            testExternalId=test_external_id,
            runId=run_id,
            testCaseHash=test_case_hash,
            evaluatorExternalId=evaluator_external_id,
            score=evaluation.score,
            threshold=dataclasses.asdict(evaluation.threshold) if evaluation.threshold else None,
            metadata=evaluation.metadata,
            revisionUsage=[usage.serialize() for usage in revision_usage] if revision_usage else None,
        ),
    )


async def send_test_case_result(
    test_external_id: str,
    run_id: str,
    test_case_ctx: TestCaseContext[TestCaseType],
    output: Any,
    test_case_duration_ms: float,
) -> None:
    # Revision usage is collected throughout a test case's run
    revision_usage = get_revision_usage()

    # Flush the logs before we send the result, since the CLI
    # accumulates the events and sends them as a batch along
    # with the result.
    flush()

    await post_to_cli(
        "/results",
        json=dict(
            testExternalId=test_external_id,
            runId=run_id,
            testCaseHash=test_case_ctx.hash(),
            testCaseBody=serialize_test_case(test_case_ctx.test_case),
            testCaseOutput=serialize_output(output),
            testCaseDurationMs=test_case_duration_ms,
            testCaseRevisionUsage=[usage.serialize() for usage in revision_usage] if revision_usage else None,
            testCaseHumanReviewInputFields=serialize_test_case_for_human_review(test_case_ctx.test_case),
            testCaseHumanReviewOutputFields=serialize_output_for_human_review(output),
        ),
    )


async def send_start_test_run(
    test_external_id: str,
    grid_search_run_group_id: Optional[str],
    grid_search_params_combo: Optional[GridSearchParamsCombo],
) -> str:
    start_resp = await post_to_cli(
        "/start",
        json=dict(
            testExternalId=test_external_id,
            gridSearchRunGroupId=grid_search_run_group_id,
            gridSearchParamsCombo=grid_search_params_combo,
        ),
    )
    if not start_resp:
        raise Exception(f"Failed to start test run for {test_external_id}")
    try:
        start_resp.raise_for_status()
    except HTTPStatusError:
        raise Exception(f"Failed to start test run for {test_external_id}")

    return start_resp.json()["id"]  # type: ignore [no-any-return]


async def send_end_test_run(
    test_external_id: str,
    run_id: str,
) -> None:
    await post_to_cli(
        "/end",
        json=dict(testExternalId=test_external_id, runId=run_id),
    )


async def send_start_grid_search_run(
    test_external_id: str,
    grid_search_params: GridSearchParams,
) -> str:
    grid_resp = await post_to_cli(
        "/grids",
        json=dict(testExternalId=test_external_id, gridSearchParams=grid_search_params),
    )
    if not grid_resp:
        raise Exception(f"Failed to start grid search run for {test_external_id}")
    try:
        grid_resp.raise_for_status()
    except HTTPStatusError:
        raise Exception(f"Failed to start grid search run for {test_external_id}")

    return grid_resp.json()["id"]  # type: ignore [no-any-return]
