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
from autoblocks.tracer import AutoblocksTracer

AUTOBLOCKS_API_KEY = os.environ.get("AUTOBLOCKS_API_KEY")
AUTOBLOCKS_INGESTION_KEY = os.environ.get("AUTOBLOCKS_INGESTION_KEY")

# We've created a view in our CI org to be used in CI tests.
# It has one filter, message == 'sdk.e2e', and its timespan is "last 1 hour"
E2E_TESTS_VIEW_ID = "cllmlk8py0003l608vd83dc03"
E2E_TESTS_EXPECTED_MESSAGE = "sdk.e2e"


def main():
    if not AUTOBLOCKS_API_KEY:
        raise Exception("AUTOBLOCKS_API_KEY is required")
    if not AUTOBLOCKS_INGESTION_KEY:
        raise Exception("AUTOBLOCKS_INGESTION_KEY is required")

    client = AutoblocksAPIClient(AUTOBLOCKS_API_KEY, timeout=timedelta(seconds=30))
    tracer = AutoblocksTracer(AUTOBLOCKS_INGESTION_KEY)

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
