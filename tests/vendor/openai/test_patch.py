import json
import os
import uuid
from datetime import datetime
from unittest import mock

import freezegun
import openai
import pytest

from autoblocks._impl.config.constants import AUTOBLOCKS_INGESTION_KEY
from autoblocks.vendor.openai import trace_openai


@pytest.fixture
def tracer():
    with mock.patch.dict(os.environ, {AUTOBLOCKS_INGESTION_KEY: "mock-ingestion-key"}):
        tracer = trace_openai()
        trace_openai()  # call multiple times to ensure that the patch is idempotent
        tracer.set_trace_id(None)  # reset the trace id
        return tracer


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(datetime(2021, 1, 1, 1, 1, 1, 1)):
        yield


timestamp = "2021-01-01T01:01:01.000001+00:00"


def decode_requests(requests):
    return [json.loads(req.content.decode()) for req in requests]


def test_patch_completion(httpx_mock, tracer):
    httpx_mock.add_response()

    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 2

    trace_ids = list(set(req["traceId"] for req in requests))
    assert len(trace_ids) == 1
    assert trace_ids[0] is not None

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


def test_patch_completion_custom_event(httpx_mock, tracer):
    httpx_mock.add_response()

    trace_id = str(uuid.uuid4())
    tracer.set_trace_id(trace_id)

    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    tracer.send_event("custom.message")

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 3

    assert all(req["traceId"] == trace_id for req in requests)

    assert requests[0]["message"] == "ai.completion.request"
    assert requests[1]["message"] == "ai.completion.response"
    assert requests[2]["message"] == "custom.message"


def test_patch_chat_completion(httpx_mock, tracer):
    httpx_mock.add_response()

    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello!"}],
    )

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 2

    trace_ids = list(set(req["traceId"] for req in requests))
    assert len(trace_ids) == 1
    assert trace_ids[0] is not None

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


def test_patch_completion_doesnt_override_trace_id(httpx_mock, tracer):
    httpx_mock.add_response()

    trace_id = str(uuid.uuid4())

    # Since we're setting our own trace_id here,
    # the patch function shouldn't generate a new one.
    tracer.set_trace_id(trace_id)

    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 2
    assert all(req["traceId"] == trace_id for req in requests)


def test_patch_completion_makes_new_trace_id_for_each_openai_call(httpx_mock, tracer):
    # We aren't setting a trace_id, so each openai call should generate its own.
    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )
    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        temperature=0,
    )
    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 4
    assert all(req["traceId"] is not None for req in requests)

    # First two should be the same trace_id and last two should be same trace_id and each group should be different
    assert requests[0]["traceId"] == requests[1]["traceId"]
    assert requests[2]["traceId"] == requests[3]["traceId"]
    assert requests[0]["traceId"] != requests[2]["traceId"]


def test_patch_completion_error(httpx_mock, tracer):
    httpx_mock.add_response()

    try:
        openai.Completion.create(
            # Invalid model
            model="fdsa",
            prompt="Say this is a test",
            temperature=0,
        )
    except openai.InvalidRequestError:
        pass

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 2

    trace_ids = list(set(req["traceId"] for req in requests))
    assert len(trace_ids) == 1
    assert trace_ids[0] is not None

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
    assert requests[1]["properties"]["error"] == "The model `fdsa` does not exist"


def test_patch_chat_completion_error(httpx_mock, tracer):
    httpx_mock.add_response()

    try:
        openai.ChatCompletion.create(
            model="fdsa",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        )
    except openai.InvalidRequestError:
        pass

    requests = decode_requests(httpx_mock.get_requests())
    assert len(requests) == 2

    trace_ids = list(set(req["traceId"] for req in requests))
    assert len(trace_ids) == 1
    assert trace_ids[0] is not None

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
    assert requests[1]["properties"]["error"] == "The model `fdsa` does not exist"
