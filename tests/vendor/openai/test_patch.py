import json
import os
import uuid
from unittest import mock

import openai

from autoblocks._impl.config.constants import AUTOBLOCKS_INGESTION_KEY
from autoblocks.vendor.openai import trace_openai

with mock.patch.dict(os.environ, {AUTOBLOCKS_INGESTION_KEY: "mock-ingestion-key"}):
    # Call multiple times to ensure that the patch is idempotent
    tracer = trace_openai()
    trace_openai()
    trace_openai()


def test_patch_completion(httpx_mock):
    httpx_mock.add_response()

    trace_id = str(uuid.uuid4())
    tracer.set_trace_id(trace_id)

    openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Say this is a test",
        max_tokens=7,
        temperature=0,
    )

    tracer.send_event("custom.message")

    requests = httpx_mock.get_requests()
    assert len(requests) == 3

    req0 = json.loads(requests[0].content.decode())
    req1 = json.loads(requests[1].content.decode())
    req2 = json.loads(requests[2].content.decode())

    assert all(req["traceId"] == trace_id for req in [req0, req1, req2])

    assert req0["message"] == "ai.completion.request"
    assert req0["timestamp"] is not None
    assert req0["properties"]["provider"] == "openai"
    assert req0["properties"]["model"] == "gpt-3.5-turbo-instruct"
    assert req0["properties"]["prompt"] == "Say this is a test"
    assert req0["properties"]["max_tokens"] == 7
    assert req0["properties"]["temperature"] == 0

    assert req1["message"] == "ai.completion.response"
    assert req1["timestamp"] is not None
    assert req1["properties"]["provider"] == "openai"
    assert req1["properties"]["latency_ms"] is not None
    assert req1["properties"]["model"] == "gpt-3.5-turbo-instruct"
    assert req1["properties"]["choices"][0]["text"] is not None
    assert req1["properties"]["usage"] is not None

    assert req2["message"] == "custom.message"


def test_patch_chat_completion(httpx_mock):
    httpx_mock.add_response()

    trace_id = str(uuid.uuid4())
    tracer.set_trace_id(trace_id)

    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello!"}],
    )

    tracer.send_event("custom.message")

    requests = httpx_mock.get_requests()
    assert len(requests) == 3

    req0 = json.loads(requests[0].content.decode())
    req1 = json.loads(requests[1].content.decode())
    req2 = json.loads(requests[2].content.decode())

    assert all(req["traceId"] == trace_id for req in [req0, req1, req2])

    assert req0["message"] == "ai.completion.request"
    assert req0["timestamp"] is not None
    assert req0["properties"]["provider"] == "openai"
    assert req0["properties"]["model"] == "gpt-3.5-turbo"
    assert req0["properties"]["temperature"] == 0
    assert req0["properties"]["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]

    assert req1["message"] == "ai.completion.response"
    assert req1["timestamp"] is not None
    assert req1["properties"]["provider"] == "openai"
    assert req1["properties"]["latency_ms"] is not None
    assert req1["properties"]["model"].startswith("gpt-3.5-turbo")
    assert req1["properties"]["choices"][0]["message"]["content"] is not None
    assert req1["properties"]["usage"] is not None

    assert req2["message"] == "custom.message"
