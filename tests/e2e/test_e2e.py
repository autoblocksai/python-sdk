import asyncio
import dataclasses
import logging
import os
import random
import signal
import subprocess
import time
import uuid
from datetime import timedelta
from unittest import mock

import httpx
import pydantic
import pytest

from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import EventFilter
from autoblocks.api.models import EventFilterOperator
from autoblocks.api.models import RelativeTimeFilter
from autoblocks.api.models import SystemEventFilterKey
from autoblocks.api.models import TraceFilter
from autoblocks.api.models import TraceFilterOperator
from autoblocks.configs.config import AutoblocksConfig
from autoblocks.configs.models import RemoteConfig
from autoblocks.prompts.models import WeightedMinorVersion
from autoblocks.testing.models import BaseTestCase
from autoblocks.testing.models import BaseTestEvaluator
from autoblocks.testing.models import Evaluation
from autoblocks.testing.run import run_test_suite
from autoblocks.tracer import AutoblocksTracer
from tests.e2e.prompts import QuestionAnswererPromptManager
from tests.e2e.prompts import TextSummarizationPromptManager
from tests.e2e.prompts import UsedByCiDontDeleteNoParamsPromptManager
from tests.e2e.prompts import UsedByCiDontDeletePromptManager
from tests.e2e.prompts import UsedByCiDontDeleteWithToolsPromptManager
from tests.util import ANY_NUMBER
from tests.util import MOCK_CLI_SERVER_ADDRESS
from tests.util import expect_cli_post_request

log = logging.getLogger(__name__)

# The below are entities in our Autoblocks CI org that we use for testing.
E2E_TESTS_VIEW_ID = "cllmlk8py0003l608vd83dc03"
E2E_TESTS_EXPECTED_MESSAGE = "sdk.e2e"
E2E_TEST_SUITE_ID = "my-test-suite"
E2E_TEST_CASE_ID = "cluh2cwla0001d590dha70npc"

client = AutoblocksAPIClient(timeout=timedelta(seconds=30), api_key=os.environ["AUTOBLOCKS_API_KEY_USER"])
tracer = AutoblocksTracer()


def wait_for_trace_to_exist(trace_id: str) -> None:
    num_tries = 10
    while num_tries:
        traces_from_view = client.get_traces_from_view(E2E_TESTS_VIEW_ID, page_size=10)

        if any(trace.id == trace_id for trace in traces_from_view.traces):
            log.info(f"Found trace {trace_id}!")
            return

        log.info(f"Trace {trace_id} not found... {num_tries} tries left.")
        time.sleep(5)
        num_tries -= 1

    raise Exception(f"Trace {trace_id} was not found.")


# apply this to all tests in this file
pytestmark = pytest.mark.httpx_mock(non_mocked_hosts=["api.autoblocks.ai"])


def test_get_views():
    # Make sure our view exists
    views = client.get_views()
    if E2E_TESTS_VIEW_ID not in (view.id for view in views):
        raise Exception(f"View {E2E_TESTS_VIEW_ID} not found!")


def test_get_test_cases():
    test_case_response = client.get_test_cases(test_suite_id=E2E_TEST_SUITE_ID)
    if E2E_TEST_CASE_ID not in (case.id for case in test_case_response.test_cases):
        raise Exception(f"Test case {E2E_TEST_CASE_ID} not found!")


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


def test_config_latest():
    # This test uses a revision created in our CI org:
    # https://app.autoblocks.ai/configs/used-by-ci-dont-delete/revisions/clvlc9qv50003urfi9h9nc6z5/edit

    class MyConfigValue(pydantic.BaseModel):
        my_val: str

    class MyConfig(AutoblocksConfig[MyConfigValue]):
        pass

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(
        config=RemoteConfig(id="used-by-ci-dont-delete", major_version="1", minor_version="latest"),
        parser=MyConfigValue.model_validate,
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


def test_config_specific_version():
    # This test uses a revision created in our CI org:
    # https://app.autoblocks.ai/configs/used-by-ci-dont-delete/revisions/clvlc9qv50003urfi9h9nc6z5/edit

    class MyConfigValue(pydantic.BaseModel):
        my_val: str

    class MyConfig(AutoblocksConfig[MyConfigValue]):
        pass

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(
        config=RemoteConfig(id="used-by-ci-dont-delete", major_version="1", minor_version="0"),
        parser=MyConfigValue.model_validate,
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


def test_config_undeployed_latest():
    # This test uses a revision created in our CI org:
    # https://app.autoblocks.ai/configs/used-by-ci-dont-delete/revisions/clvlcgpiq0003qtvsbz5vt7e0/edit

    class MyConfigValue(pydantic.BaseModel):
        my_val: str

    class MyConfig(AutoblocksConfig[MyConfigValue]):
        pass

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(
        config=RemoteConfig(id="used-by-ci-dont-delete", dangerously_use_undeployed_revision="latest"),
        parser=MyConfigValue.model_validate,
        # Need to use a user-scoped API key to access undeployed configs
        api_key=os.environ["AUTOBLOCKS_API_KEY_USER"],
    )

    assert config.value == MyConfigValue(my_val="val-from-remote-undeployed")


def test_config_undeployed_revision():
    # This test uses a revision created in our CI org:
    # https://app.autoblocks.ai/configs/used-by-ci-dont-delete/revisions/clvlcgpiq0003qtvsbz5vt7e0/edit

    class MyConfigValue(pydantic.BaseModel):
        my_val: str

    class MyConfig(AutoblocksConfig[MyConfigValue]):
        pass

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(
        config=RemoteConfig(
            id="used-by-ci-dont-delete",
            dangerously_use_undeployed_revision="clvv48mlc0003ximd4htzat8w",
        ),
        parser=MyConfigValue.model_validate,
        # Need to use a user-scoped API key to access undeployed configs
        api_key=os.environ["AUTOBLOCKS_API_KEY_USER"],
    )

    assert config.value == MyConfigValue(my_val="val-from-remote-undeployed")


def test_prompt_manager():
    mgr = UsedByCiDontDeletePromptManager(
        minor_version="0",
    )

    with mgr.exec() as ctx:
        assert ctx.params.max_tokens == 256
        assert ctx.params.model == "gpt-4"
        assert ctx.params.temperature == 0.3
        assert ctx.params.top_p == 1
        assert ctx.params.frequency_penalty == 0
        assert ctx.params.presence_penalty == 0.6
        assert ctx.params.seed == 4096
        assert ctx.params.response_format == {"type": "json_object"}

        assert (
            ctx.render_template.template_a(
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today!"
        )

        assert (
            ctx.render_template.template_b(
                name="Alice",
            )
            == "My name is Alice."
        )

        assert ctx.render_template.template_c() == "I am template c and I have no params"

        assert ctx.track() == {
            "id": "used-by-ci-dont-delete",
            "version": "6.0",
            "revisionId": "cm6gsq0t60003nbscwcqkdgat",
            "params": {
                "params": {
                    "maxTokens": 256,
                    "model": "gpt-4",
                    "stopSequences": [],
                    "temperature": 0.3,
                    "topP": 1,
                    "frequencyPenalty": 0,
                    "presencePenalty": 0.6,
                    "seed": 4096,
                    "responseFormat": {"type": "json_object"},
                },
            },
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today!",
                },
                {
                    "id": "template-b",
                    "template": "My name is {{ name }}.",
                },
                {
                    "id": "template-c",
                    "template": "I am template c and I have no params",
                },
            ],
            "tools": [],
        }


def test_prompt_manager_latest():
    mgr = UsedByCiDontDeletePromptManager(
        minor_version="latest",
    )

    with mgr.exec() as ctx:
        assert ctx.params.max_tokens == 256
        assert ctx.params.model == "gpt-4"
        assert ctx.params.temperature == 0.3
        assert ctx.params.top_p == 1
        assert ctx.params.frequency_penalty == 0
        assert ctx.params.presence_penalty == 0.6
        assert ctx.params.seed == 4096
        assert ctx.params.response_format == {"type": "json_object"}

        assert (
            ctx.render_template.template_a(
                name="Alice",
                weather="sunny",
            )
            == "Hello, Alice! The weather is sunny today!"
        )

        assert (
            ctx.render_template.template_b(
                name="Alice",
            )
            == "My name is Alice!"
        )

        assert ctx.render_template.template_c() == "I am template c and I have no params"

        assert ctx.track() == {
            "id": "used-by-ci-dont-delete",
            "version": "6.1",
            "revisionId": "cm6gswg4z000b11nw5dyqmvqw",
            "params": {
                "params": {
                    "maxTokens": 256,
                    "model": "gpt-4",
                    "stopSequences": [],
                    "temperature": 0.3,
                    "topP": 1,
                    "frequencyPenalty": 0,
                    "presencePenalty": 0.6,
                    "seed": 4096,
                    "responseFormat": {"type": "json_object"},
                },
            },
            "templates": [
                {
                    "id": "template-a",
                    "template": "Hello, {{ name }}! The weather is {{ weather }} today!",
                },
                {
                    "id": "template-b",
                    "template": "My name is {{ name }}!",
                },
                {
                    "id": "template-c",
                    "template": "I am template c and I have no params",
                },
            ],
            "tools": [],
        }


def test_prompt_manager_weighted():
    mgr = UsedByCiDontDeletePromptManager(
        [
            WeightedMinorVersion(
                version="latest",
                weight=1,
            ),
            WeightedMinorVersion(
                version="0",
                weight=1,
            ),
        ]
    )

    with mgr.exec() as ctx:
        assert ctx.params.model == "gpt-4"
        assert ctx.track()["version"] in ("6.0", "6.1")


def test_prompt_manager_no_model_params():
    mgr = UsedByCiDontDeleteNoParamsPromptManager(
        minor_version="0",
    )

    with mgr.exec() as prompt:
        with pytest.raises(AttributeError):
            # This should raise an AttributeError because the prompt has no params
            prompt.params.model  # type: ignore[attr-defined]

        assert prompt.track() == dict(
            id="used-by-ci-dont-delete-no-params",
            version="1.0",
            revisionId="clvgwh7on003kkasy8cltjobg",
            params=None,
            templates=[
                dict(id="my-template-id", template="Hello, {{ name }}!"),
            ],
            tools=None,
        )


def test_prompt_manager_with_tools():
    mgr = UsedByCiDontDeleteWithToolsPromptManager(
        minor_version="0",
    )

    with mgr.exec() as prompt:
        assert prompt.render_tool.my_tool(description="my description") == dict(
            type="function",
            function=dict(
                name="MyTool",
                description="This is the description",
                parameters=dict(
                    type="object",
                    properties=dict(
                        myParam=dict(type="string", description="my description"),
                    ),
                    required=["myParam"],
                ),
            ),
        )
        assert prompt.track() == dict(
            id="used-by-ci-dont-delete-with-tools",
            version="1.0",
            revisionId="clyq8mdh90003ltgk9se55nxk",
            params=None,
            templates=[
                dict(id="system", template="System Template"),
            ],
            tools=[
                dict(
                    type="function",
                    function=dict(
                        name="MyTool",
                        description="This is the description",
                        parameters=dict(
                            type="object",
                            properties=dict(
                                myParam=dict(type="string", description="{{ description }}"),
                            ),
                            required=["myParam"],
                        ),
                    ),
                )
            ],
        )


def test_prompt_manager_undeployed_latest_revision():
    mgr = TextSummarizationPromptManager(
        # Need to use a user-scoped API key to access undeployed prompts
        api_key=os.environ["AUTOBLOCKS_API_KEY_USER"],
        # Request the latest revision
        minor_version="latest",
    )

    with mgr.exec() as prompt:
        assert prompt.track()["id"] == "text-summarization"
        assert prompt.track()["version"] == f"revision:{prompt.track()['revisionId']}"


def test_prompt_manager_undeployed_specific_revision():
    """
    This test uses a revision created in our CI org:

        https://app.autoblocks.ai/prompts/question-answerer/revisions/clvodtv700003a2z02fumceby/edit
    """
    mgr = QuestionAnswererPromptManager(
        # Need to use a user-scoped API key to access undeployed prompts
        # TODO: allow org-wide keys to retrieve shared prompts
        api_key=os.environ["AUTOBLOCKS_API_KEY_USER"],
        # Request a specific revision
        minor_version="clvodtv700003a2z02fumceby",
    )

    with mgr.exec() as prompt:
        assert prompt.track()["id"] == "question-answerer"
        assert prompt.track()["version"] == "revision:clvodtv700003a2z02fumceby"
        assert prompt.track()["revisionId"] == "clvodtv700003a2z02fumceby"


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
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id="mock-run-id"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/results",
        body=dict(
            testExternalId="my-test-id",
            runId="mock-run-id",
            testCaseHash="hash",
            testCaseBody={"x": 1},
            testCaseOutput="gpt-4",
            testCaseDurationMs=ANY_NUMBER,
            testCaseRevisionUsage=[
                dict(
                    entityExternalId="used-by-ci-dont-delete",
                    entityType="prompt",
                    revisionId="cm6gswg4z000b11nw5dyqmvqw",
                    usedAt=mock.ANY,
                ),
            ],
            testCaseHumanReviewInputFields=None,
            testCaseHumanReviewOutputFields=None,
            datasetItemId=None,
        ),
        json=dict(id="mock-result-id-1"),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/evals",
        body=dict(
            testExternalId="my-test-id",
            runId="mock-run-id",
            testCaseHash="hash",
            evaluatorExternalId="my-evaluator",
            score=0.97,
            threshold=None,
            metadata=None,
            revisionUsage=[
                dict(
                    entityExternalId="used-by-ci-dont-delete-no-params",
                    entityType="prompt",
                    revisionId="clvgwh7on003kkasy8cltjobg",
                    usedAt=mock.ANY,
                ),
            ],
            assertions=None,
        ),
    )
    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId="mock-run-id",
        ),
    )

    @dataclasses.dataclass
    class MyTestCase(BaseTestCase):
        x: int

        def hash(self):
            return "hash"

    def test_fn(test_case: MyTestCase) -> str:
        mgr = UsedByCiDontDeletePromptManager(
            minor_version="1",
        )
        with mgr.exec() as prompt:
            return prompt.params.model

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        mgr = UsedByCiDontDeleteNoParamsPromptManager(
            minor_version="0",
        )

        def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            with self.mgr.exec():
                pass
            return Evaluation(score=0.97)

    run_test_suite(
        id="my-test-id",
        test_cases=[
            MyTestCase(x=1),
        ],
        evaluators=[MyEvaluator()],
        fn=test_fn,
    )


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


def test_async_script_flushes_on_exit():
    # Run the script
    test_trace_id = str(uuid.uuid4())
    sleep_seconds = 10
    process = subprocess.Popen(
        ["python", "async_script.py", test_trace_id, f"{sleep_seconds}"],
        cwd="tests/e2e",
        env=dict(os.environ, **{"PYTHONPATH": os.getcwd()}),
    )

    # Wait for the process to terminate
    process.wait()
    log.info(f"Process {process.pid} terminated with return code {process.returncode}.")

    wait_for_trace_to_exist(test_trace_id)


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
    },
)
def test_many_test_cases(httpx_mock):
    @dataclasses.dataclass
    class MyTestCase(BaseTestCase):
        x: int

        def hash(self):
            return f"{self.x}"

    async def test_fn(test_case: MyTestCase) -> str:
        return f"{test_case.x}"

    class MyEvaluator(BaseTestEvaluator):
        id = "my-evaluator"

        async def evaluate_test_case(self, test_case: MyTestCase, output: str) -> Evaluation:
            return Evaluation(score=0.97)

    test_cases = [MyTestCase(x=i) for i in range(0, 100)]

    expect_cli_post_request(
        httpx_mock,
        path="/start",
        body=dict(
            testExternalId="my-test-id",
            gridSearchRunGroupId=None,
            gridSearchParamsCombo=None,
        ),
        json=dict(id="mock-run-id"),
    )

    # simulate network latency so the semaphores get triggered
    async def simulate_network_latency(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Random delay between 100ms and 500ms
        return httpx.Response(
            status_code=200,
            json=dict(id=f"mock-result-id-{i}"),
        )

    for i in range(0, 100):
        # add one for /results and one for /evals
        httpx_mock.add_callback(simulate_network_latency)
        httpx_mock.add_callback(simulate_network_latency)

    expect_cli_post_request(
        httpx_mock,
        path="/end",
        body=dict(
            testExternalId="my-test-id",
            runId="mock-run-id",
        ),
    )

    run_test_suite(
        id="my-test-id", test_cases=test_cases, evaluators=[MyEvaluator()], fn=test_fn, max_test_case_concurrency=100
    )


def test_get_dataset():
    dataset = client.get_dataset("Test Dataset", "1")
    assert dataset.revision_id == "cm1mgsnx1000bf9f85p99kx3g"
    assert dataset.name == "Test Dataset"
    assert dataset.schema_version == "1"
    assert len(dataset.items) == 1
    assert dataset.items[0].splits == ["test-split"]
    assert dataset.items[0].data == {"Test Property": "Test Value 2"}


def test_get_dataset_by_splits():
    dataset = client.get_dataset("Test Dataset", "1", splits=["test-split-2"])
    assert dataset.revision_id == "cm1mgsnx1000bf9f85p99kx3g"
    assert dataset.name == "Test Dataset"
    assert dataset.schema_version == "1"
    assert len(dataset.items) == 0


def test_get_dataset_by_revision_id():
    dataset = client.get_dataset("Test Dataset", "1", revision_id="cm1mgsgu30006f9f85zhuwzlx")
    assert dataset.revision_id == "cm1mgsgu30006f9f85zhuwzlx"
    assert dataset.name == "Test Dataset"
    assert dataset.schema_version == "1"
    assert len(dataset.items) == 1
    assert dataset.items[0].splits == ["test-split"]
    assert dataset.items[0].data == {"Test Property": "Test Value"}


def test_get_dataset_by_revision_id_and_splits():
    dataset = client.get_dataset("Test Dataset", "1", revision_id="cm1mgsgu30006f9f85zhuwzlx", splits=["test-split-2"])
    assert dataset.revision_id == "cm1mgsgu30006f9f85zhuwzlx"
    assert dataset.name == "Test Dataset"
    assert dataset.schema_version == "1"
    assert len(dataset.items) == 0
