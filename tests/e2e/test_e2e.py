import dataclasses
import logging
import os
import signal
import subprocess
import time
import uuid
from datetime import timedelta
from unittest import mock

import httpx
import pytest

from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import EventFilter
from autoblocks.api.models import EventFilterOperator
from autoblocks.api.models import RelativeTimeFilter
from autoblocks.api.models import SystemEventFilterKey
from autoblocks.api.models import TraceFilter
from autoblocks.api.models import TraceFilterOperator
from autoblocks.prompts.models import WeightedMinorVersion
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.run import run_test_suite
from autoblocks.tracer import AutoblocksTracer
from tests.e2e.prompts import UsedByCiDontDeleteMinorVersion
from tests.e2e.prompts import UsedByCiDontDeleteNoParamsMinorVersion
from tests.e2e.prompts import UsedByCiDontDeleteNoParamsPromptManager
from tests.e2e.prompts import UsedByCiDontDeleteNoParamsUndeployedMinorVersion
from tests.e2e.prompts import UsedByCiDontDeleteNoParamsUndeployedPromptManager
from tests.e2e.prompts import UsedByCiDontDeletePromptManager
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import expect_cli_post_request

log = logging.getLogger(__name__)

# The below are entities in our Autoblocks CI org that we use for testing.
E2E_TESTS_DATASET_ID = "clpup7f9400075us75nin99f0"
E2E_TESTS_VIEW_ID = "cllmlk8py0003l608vd83dc03"
E2E_TESTS_TRACE_ID = "4943bb26-3526-4e9c-bcd1-62f08baa621a"
E2E_TESTS_EXPECTED_MESSAGE = "sdk.e2e"

client = AutoblocksAPIClient(timeout=timedelta(seconds=30))
tracer = AutoblocksTracer()


@pytest.fixture
def non_mocked_hosts() -> list[str]:
    """
    Don't mock requests to our API.

    https://colin-b.github.io/pytest_httpx/#do-not-mock-some-requests
    """
    return ["api.autoblocks.ai"]


def test_get_datasets():
    # Make sure dataset and items exists
    datasets = client.get_datasets()
    if E2E_TESTS_DATASET_ID not in (dataset.id for dataset in datasets):
        raise Exception(f"Dataset {E2E_TESTS_DATASET_ID} not found!")

    dataset = client.get_dataset(E2E_TESTS_DATASET_ID)
    if len(dataset.items) == 0:
        raise Exception(f"Dataset {E2E_TESTS_DATASET_ID} is empty!")


def test_get_trace():
    # Test that we can fetch a trace by ID
    trace = client.get_trace(E2E_TESTS_TRACE_ID)
    print(f"Found trace {trace.id}!")
    assert trace.id == E2E_TESTS_TRACE_ID
    assert trace.events[0].id == "ee9dd0c7-daa4-4086-8d6c-b9706f435a68"
    assert trace.events[0].trace_id == E2E_TESTS_TRACE_ID
    assert trace.events[0].message == "langchain.chain.start"
    assert trace.events[0].timestamp == "2023-12-11T12:27:26.831Z"
    assert trace.events[0].properties["inputs"]["input"] == "What is today's date? What is that date divided by 2?"


def test_get_views():
    # Make sure our view exists
    views = client.get_views()
    if E2E_TESTS_VIEW_ID not in (view.id for view in views):
        raise Exception(f"View {E2E_TESTS_VIEW_ID} not found!")


def test_send_and_retrieve_event():
    # Send test event
    test_trace_id = str(uuid.uuid4())
    print(f"{test_trace_id=}")
    tracer.send_event(E2E_TESTS_EXPECTED_MESSAGE, trace_id=test_trace_id)

    retries = 10
    page_size = 10

    while True:
        page_from_view = client.get_traces_from_view(E2E_TESTS_VIEW_ID, page_size=page_size)
        page_from_search = client.search_traces(
            page_size=page_size,
            time_filter=RelativeTimeFilter(hours=1),
            trace_filters=[
                TraceFilter(
                    operator=TraceFilterOperator.CONTAINS,
                    event_filters=[
                        EventFilter(
                            key=SystemEventFilterKey.MESSAGE,
                            value=E2E_TESTS_EXPECTED_MESSAGE,
                            operator=EventFilterOperator.EQUALS,
                        ),
                    ],
                ),
            ],
        )

        trace_in_view = any(trace.id == test_trace_id for trace in page_from_view.traces)
        trace_in_search = any(trace.id == test_trace_id for trace in page_from_search.traces)

        if trace_in_view and trace_in_search:
            print(f"Found trace {test_trace_id}!")
            break

        retries -= 1

        if retries == 0:
            raise Exception(f"Couldn't find trace {test_trace_id}.")

        sleep_seconds = 5
        print(f"Couldn't find trace {test_trace_id} yet, waiting {sleep_seconds} seconds. {retries} tries left.")
        time.sleep(sleep_seconds)


def test_prompt_manager():
    mgr = UsedByCiDontDeletePromptManager(
        UsedByCiDontDeleteMinorVersion.v1,
    )

    with mgr.exec() as ctx:
        assert ctx.params.frequency_penalty == 0
        assert ctx.params.max_tokens == 256
        assert ctx.params.model == "gpt-4"
        assert ctx.params.presence_penalty == -0.3
        assert ctx.params.temperature == 0.7
        assert ctx.params.top_p == 1

        assert (
            ctx.render.template_a(
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today."
        )

        # # TODO: add support for optional params
        # assert ctx.render.template_b(
        #     name="Alice",
        # ) == "Hello! My name is Alice."

        assert (
            ctx.render.template_b(
                name="Alice",
                optional="Bob",
            )
            == "Hello Bob! My name is Alice."
        )

        assert ctx.render.template_c() == "I am template c and I have no params"

        assert ctx.track() == {
            "id": "used-by-ci-dont-delete",
            "version": "2.1",
            "params": {
                "version": "1.1",
                "params": {
                    "frequencyPenalty": 0,
                    "maxTokens": 256,
                    "model": "gpt-4",
                    "presencePenalty": -0.3,
                    "stopSequences": [],
                    "temperature": 0.7,
                    "topP": 1,
                },
            },
            "templates": [
                {
                    "id": "template-a",
                    "version": "1.0",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today.",
                },
                {
                    "id": "template-b",
                    "version": "1.1",
                    "template": "Hello {{ optional? }}! My name is {{ name }}.",
                },
                {
                    "id": "template-c",
                    "version": "1.0",
                    "template": "I am template c and I have no params",
                },
            ],
        }


def test_prompt_manager_latest():
    mgr = UsedByCiDontDeletePromptManager(
        UsedByCiDontDeleteMinorVersion.LATEST,
    )

    with mgr.exec() as ctx:
        assert ctx.params.model == "gpt-4"
        assert ctx.track()["version"] == "2.3"


def test_prompt_manager_weighted():
    mgr = UsedByCiDontDeletePromptManager(
        [
            WeightedMinorVersion(
                version=UsedByCiDontDeleteMinorVersion.LATEST,
                weight=1,
            ),
            WeightedMinorVersion(
                version=UsedByCiDontDeleteMinorVersion.v0,
                weight=1,
            ),
        ]
    )

    with mgr.exec() as ctx:
        assert ctx.params.model == "gpt-4"
        assert ctx.track()["version"] in ("2.0", "2.3")


def test_prompt_manager_no_model_params():
    mgr = UsedByCiDontDeleteNoParamsPromptManager(
        UsedByCiDontDeleteNoParamsMinorVersion.v0,
    )

    with mgr.exec() as prompt:
        assert prompt.params is None

        assert prompt.track() == dict(
            id="used-by-ci-dont-delete-no-params",
            version="1.0",
            params=None,
            templates=[
                dict(id="my-template-id", version="1.0", template="Hello, {{ name }}!"),
            ],
        )


def test_prompt_manager_no_model_params_undeployed():
    mgr = UsedByCiDontDeleteNoParamsUndeployedPromptManager(
        UsedByCiDontDeleteNoParamsUndeployedMinorVersion.DANGEROUSLY_USE_UNDEPLOYED,
    )

    with mgr.exec() as prompt:
        assert prompt.params is None

        assert prompt.track()["id"] == "used-by-ci-dont-delete-no-params"
        assert prompt.track()["version"] == "undeployed"
        assert prompt.track().get("params") is None


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
    },
)
def test_init_prompt_manager_inside_test_suite(httpx_mock):
    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(testExternalId="my-test-id"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            testCaseHash="hash",
            testCaseBody={"x": 1},
            testCaseOutput="gpt-4",
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(testExternalId="my-test-id"),
    )

    @dataclasses.dataclass
    class MyTestCase(BaseTestCase):
        x: int

        def hash(self):
            return "hash"

    def test_fn(test_case: MyTestCase) -> str:
        mgr = UsedByCiDontDeletePromptManager(
            UsedByCiDontDeleteMinorVersion.v1,
        )
        with mgr.exec() as prompt:
            return prompt.params.model

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(x=1),
        ],
        evaluators=[],
        fn=test_fn,
    )


def wait_for_trace_to_exist(trace_id: str) -> None:
    num_tries = 30
    while num_tries:
        try:
            client.get_trace(trace_id)
            log.info(f"Found trace {trace_id} with {num_tries} tries remaining")
            return
        except httpx.HTTPStatusError:
            pass

        log.info(f"Trace {trace_id} not found... {num_tries} tries left.")
        time.sleep(1)
        num_tries -= 1

    raise Exception(f"Trace {trace_id} was not sent.")


def test_flask_app_flushes_on_sigterm():
    sig = signal.SIGTERM

    # Start the Flask app
    process = subprocess.Popen(
        ["gunicorn", "flask_app:app"],
        cwd="tests/e2e",
        env=dict(os.environ, **{"PYTHONPATH": os.getcwd()}),
    )

    # Give it a sec to start up
    time.sleep(1)

    # Send event
    test_trace_id = str(uuid.uuid4())
    sleep_seconds = 10
    log.info(f"Sending request to Flask app with trace ID {test_trace_id}")
    httpx.post(
        "http://localhost:8000",
        json=dict(
            trace_id=test_trace_id,
            # This is how long the evaluator is going to sleep
            sleep_seconds=sleep_seconds,
        ),
        # We should get a response quickly though
        # because the event is sent in the background
        timeout=1,
    )
    log.info("Received response from Flask app")

    # Shut down the Flask app
    log.info(f"Killing process {process.pid} with signal {sig}...")
    os.kill(process.pid, sig)

    # Wait for the process to terminate
    process.wait()
    log.info(f"Process {process.pid} terminated with return code {process.returncode}.")

    wait_for_trace_to_exist(test_trace_id)


def test_plain_script_flushes_on_exit():
    # Run the script
    test_trace_id = str(uuid.uuid4())
    sleep_seconds = 10
    process = subprocess.Popen(
        ["python", "plain_script.py", test_trace_id, f"{sleep_seconds}"],
        cwd="tests/e2e",
        env=dict(os.environ, **{"PYTHONPATH": os.getcwd()}),
    )

    # Wait for the process to terminate
    process.wait()
    log.info(f"Process {process.pid} terminated with return code {process.returncode}.")

    wait_for_trace_to_exist(test_trace_id)
