import os
import time
import uuid
from datetime import timedelta

from autoblocks.api.client import AutoblocksAPIClient
from autoblocks.api.models import EventFilter
from autoblocks.api.models import EventFilterOperator
from autoblocks.api.models import RelativeTimeFilter
from autoblocks.api.models import SystemEventFilterKey
from autoblocks.api.models import TraceFilter
from autoblocks.api.models import TraceFilterOperator
from autoblocks.prompts.models import WeightedMinorVersion
from autoblocks.tracer import AutoblocksTracer

from .prompts import UsedByCiDontDeleteMinorVersion
from .prompts import UsedByCiDontDeletePromptManager

AUTOBLOCKS_API_KEY = os.environ.get("AUTOBLOCKS_API_KEY")
AUTOBLOCKS_INGESTION_KEY = os.environ.get("AUTOBLOCKS_INGESTION_KEY")

# The below are entities in our Autoblocks CI org that we use for testing.
E2E_TESTS_DATASET_ID = "clpup7f9400075us75nin99f0"
E2E_TESTS_VIEW_ID = "cllmlk8py0003l608vd83dc03"
E2E_TESTS_TRACE_ID = "4943bb26-3526-4e9c-bcd1-62f08baa621a"
E2E_TESTS_EXPECTED_MESSAGE = "sdk.e2e"


def main():
    if not AUTOBLOCKS_API_KEY:
        raise Exception("AUTOBLOCKS_API_KEY is required")
    if not AUTOBLOCKS_INGESTION_KEY:
        raise Exception("AUTOBLOCKS_INGESTION_KEY is required")

    client = AutoblocksAPIClient(AUTOBLOCKS_API_KEY, timeout=timedelta(seconds=30))
    tracer = AutoblocksTracer(AUTOBLOCKS_INGESTION_KEY)

    # Make sure dataset and items exists
    datasets = client.get_datasets()
    if E2E_TESTS_DATASET_ID not in (dataset.id for dataset in datasets):
        raise Exception(f"Dataset {E2E_TESTS_DATASET_ID} not found!")

    dataset = client.get_dataset(E2E_TESTS_DATASET_ID)
    if len(dataset.items) == 0:
        raise Exception(f"Dataset {E2E_TESTS_DATASET_ID} is empty!")

    # Test that we can fetch a trace by ID
    trace = client.get_trace(E2E_TESTS_TRACE_ID)
    print(f"Found trace {trace.id}!")
    assert trace.id == E2E_TESTS_TRACE_ID
    assert trace.events[0].id == "ee9dd0c7-daa4-4086-8d6c-b9706f435a68"
    assert trace.events[0].trace_id == E2E_TESTS_TRACE_ID
    assert trace.events[0].message == "langchain.chain.start"
    assert trace.events[0].timestamp == "2023-12-11T12:27:26.831Z"
    assert trace.events[0].properties["inputs"]["input"] == "What is today's date? What is that date divided by 2?"

    # Make sure our view exists
    views = client.get_views()
    if E2E_TESTS_VIEW_ID not in (view.id for view in views):
        raise Exception(f"View {E2E_TESTS_VIEW_ID} not found!")

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

    test_prompt_manager()
    test_prompt_manager_latest()
    test_prompt_manager_weighted()


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
