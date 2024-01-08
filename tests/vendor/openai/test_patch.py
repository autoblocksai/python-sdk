import json
import os
import uuid
from datetime import datetime
from unittest import mock

import freezegun
import openai
import pytest

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks.vendor.openai import trace_openai

client = openai.OpenAI()

timestamp = "2021-01-01T01:01:01.000001+00:00"


@pytest.fixture
def tracer():
    with mock.patch.dict(os.environ, {"AUTOBLOCKS_INGESTION_KEY": "mock-ingestion-key"}):
        tracer = trace_openai()
        trace_openai()  # call multiple times to ensure that the patch is idempotent
        tracer.set_trace_id(None)  # reset the trace id
        return tracer


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(datetime(2021, 1, 1, 1, 1, 1, 1)):
        yield


@pytest.fixture
def httpx(httpx_mock):
    httpx_mock.add_response(
        url=INGESTION_ENDPOINT,
        headers={"content-type": "application/json"},
        json={"traceId": "mock-trace-id"},
    )
    return httpx_mock


@pytest.fixture
def non_mocked_hosts():
    """Prevents pytest-httpx from mocking out calls to OpenAI."""
    return ["api.openai.com"]


def decode_requests(requests):
    return [json.loads(req.content.decode()) for req in requests]


def check_trace_ids(requests):
    # There should be one unique trace_id and it shouldn't be None
    trace_ids = list(set(req["traceId"] for req in requests))
    assert len(trace_ids) == 1
    assert trace_ids[0] is not None


def check_span_ids(requests):
    # There should be one unique span_id and it shouldn't be None
    span_ids = list(set(req["properties"]["span_id"] for req in requests))
    assert len(span_ids) == 1
    assert span_ids[0] is not None


def test_patch_completion(httpx, tracer):
    client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 2

    check_trace_ids(requests)
    check_span_ids(requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[0]["timestamp"] == timestamp
    assert requests[0]["properties"]["provider"] == "openai"
    assert requests[0]["properties"]["model"] == "gpt-3.5-turbo-instruct"
    assert requests[0]["properties"]["prompt"] == "Say this is a test"
    assert requests[0]["properties"]["temperature"] == 0

    assert "api_key" not in requests[0]
    assert "api_base" not in requests[0]
    assert "organization" not in requests[0]

    assert requests[1]["message"] == "ai.completion.response"
    assert requests[1]["timestamp"] == timestamp
    assert requests[1]["properties"]["provider"] == "openai"
    assert requests[1]["properties"]["latency_ms"] is not None
    assert requests[1]["properties"]["model"] == "gpt-3.5-turbo-instruct"
    assert requests[1]["properties"]["choices"][0]["text"] is not None
    assert requests[1]["properties"]["usage"] is not None


def test_patch_completion_custom_event(httpx, tracer):
    trace_id = str(uuid.uuid4())
    tracer.set_trace_id(trace_id)

    client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    tracer.send_event("custom.message")

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 3

    assert all(req["traceId"] == trace_id for req in requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[1]["message"] == "ai.completion.response"
    assert requests[2]["message"] == "custom.message"

    # The first two events should have the same span_id and the 3rd shouldn't have one
    assert requests[0]["properties"]["span_id"] == requests[1]["properties"]["span_id"]
    assert requests[0]["properties"]["span_id"] is not None
    assert "span_id" not in requests[2]["properties"]


def test_patch_chat_completion(httpx, tracer):
    client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello!"}],
    )

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 2

    check_trace_ids(requests)
    check_span_ids(requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[0]["timestamp"] == timestamp
    assert requests[0]["properties"]["provider"] == "openai"
    assert requests[0]["properties"]["model"] == "gpt-3.5-turbo"
    assert requests[0]["properties"]["temperature"] == 0
    assert requests[0]["properties"]["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]

    assert "api_key" not in requests[0]
    assert "api_base" not in requests[0]
    assert "organization" not in requests[0]

    assert requests[1]["message"] == "ai.completion.response"
    assert requests[1]["timestamp"] == timestamp
    assert requests[1]["properties"]["provider"] == "openai"
    assert requests[1]["properties"]["latency_ms"] is not None
    assert requests[1]["properties"]["model"].startswith("gpt-3.5-turbo")
    assert requests[1]["properties"]["choices"][0]["message"]["content"] is not None
    assert requests[1]["properties"]["usage"] is not None


def test_patch_completion_doesnt_override_trace_id(httpx, tracer):
    trace_id = str(uuid.uuid4())

    # Since we're setting our own trace_id here,
    # the patch function shouldn't generate a new one.
    tracer.set_trace_id(trace_id)

    client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 2
    assert all(req["traceId"] == trace_id for req in requests)


def test_patch_completion_makes_new_trace_id_for_each_openai_call(httpx, tracer):
    # We aren't setting a trace_id, so each openai call should generate its own.
    client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )
    client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )
    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 4
    assert all(req["traceId"] is not None for req in requests)

    # First two should be the same trace_id and last two should be same trace_id and each group should be different
    assert requests[0]["traceId"] == requests[1]["traceId"]
    assert requests[2]["traceId"] == requests[3]["traceId"]
    assert requests[0]["traceId"] != requests[2]["traceId"]

    # First two should be the same span_id and last two should be same span_id and each group should be different
    assert requests[0]["properties"]["span_id"] == requests[1]["properties"]["span_id"]
    assert requests[2]["properties"]["span_id"] == requests[3]["properties"]["span_id"]
    assert requests[0]["properties"]["span_id"] != requests[2]["properties"]["span_id"]


def test_patch_completion_error(httpx, tracer):
    try:
        client.completions.create(
            # Invalid model
            model="fdsa",
            prompt="Say this is a test",
            temperature=0,
        )
    except openai.NotFoundError:
        pass

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 2

    check_trace_ids(requests)
    check_span_ids(requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[0]["timestamp"] == timestamp
    assert requests[0]["properties"]["provider"] == "openai"
    assert requests[0]["properties"]["model"] == "fdsa"
    assert requests[0]["properties"]["prompt"] == "Say this is a test"
    assert requests[0]["properties"]["temperature"] == 0

    assert requests[1]["message"] == "ai.completion.error"
    assert requests[1]["timestamp"] == timestamp
    assert requests[1]["properties"]["provider"] == "openai"
    assert requests[1]["properties"]["latency_ms"] is not None
    assert (
        requests[1]["properties"]["error"]
        == "Error code: 404 - {'error': {'message': 'The model `fdsa` does not exist', "
        "'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}"
    )


def test_patch_chat_completion_error(httpx, tracer):
    try:
        client.chat.completions.create(
            model="fdsa",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        )
    except openai.NotFoundError:
        pass

    requests = decode_requests(httpx.get_requests())
    assert len(requests) == 2

    check_trace_ids(requests)
    check_span_ids(requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[0]["timestamp"] == timestamp
    assert requests[0]["properties"]["provider"] == "openai"
    assert requests[0]["properties"]["model"] == "fdsa"
    assert requests[0]["properties"]["temperature"] == 0
    assert requests[0]["properties"]["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]

    assert requests[1]["message"] == "ai.completion.error"
    assert requests[1]["timestamp"] == timestamp
    assert requests[1]["properties"]["provider"] == "openai"
    assert requests[1]["properties"]["latency_ms"] is not None
    assert (
        requests[1]["properties"]["error"]
        == "Error code: 404 - {'error': {'message': 'The model `fdsa` does not exist', "
        "'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}"
    )
