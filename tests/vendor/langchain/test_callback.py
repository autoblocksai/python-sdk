import os
import uuid
from unittest import mock

import langchain
import pytest
from langchain.agents import AgentType
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain
from langchain.llms import OpenAI
from langchain.tools import Tool

from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks.vendor.langchain import AutoblocksCallbackHandler
from tests.autoblocks.util import decode_request_body


def decode_requests(requests):
    return [decode_request_body(req) for req in requests]


@pytest.fixture
def handler():
    with mock.patch.dict(os.environ, {AutoblocksEnvVar.INGESTION_KEY.value: "mock-ingestion-key"}):
        return AutoblocksCallbackHandler()


@pytest.fixture
def httpx(httpx_mock):
    httpx_mock.add_response(json=dict(traceId="mock-trace-id"))
    return httpx_mock


def test_callback_handler_filter(handler):
    assert handler._filter("sk-123") == "<redacted>"
    assert handler._filter(dict(api_key="123")) == dict()
    assert handler._filter(dict(x=dict(y=dict(api_key="1234", z="123")))) == dict(x=dict(y=dict(z="123")))
    assert handler._filter(dict(x=dict(y=dict(z="sk-123")))) == dict(x=dict(y=dict(z="<redacted>")))


def test_callback_sends_langchain_version(httpx, handler):
    llm = OpenAI()
    llm.predict("hi!", callbacks=[handler])

    for req in decode_requests(httpx.get_requests()):
        assert req["properties"]["__langchainVersion"] == langchain.__version__
        assert req["properties"]["__langchainLanguage"] == "python"


def test_callback_resets_trace_id_between_calls(httpx, handler):
    llm = OpenAI()

    # First call
    llm.predict("hi!", callbacks=[handler])
    # Second call
    llm.predict("hello!", callbacks=[handler])

    requests = decode_requests(httpx.get_requests())

    messages = [req["message"] for req in requests]
    trace_ids = [req["traceId"] for req in requests]

    assert messages == [
        # First call
        "langchain.llm.start",
        "langchain.llm.end",
        # Second call
        "langchain.llm.start",
        "langchain.llm.end",
    ]

    assert all(trace_id is not None for trace_id in trace_ids)

    # First two trace ids should be the same
    assert trace_ids[0] == trace_ids[1]
    # Second two trace ids should be the same
    assert trace_ids[2] == trace_ids[3]
    # First and second trace ids should be different
    assert trace_ids[0] != trace_ids[2]


def test_callback_respects_trace_id_set_by_user(httpx, handler):
    mock_trace_id = str(uuid.uuid4())
    handler.tracer.set_trace_id(mock_trace_id)

    llm = OpenAI()
    llm.predict("hi!", callbacks=[handler])

    handler.tracer.send_event("my.custom.event")

    requests = decode_requests(httpx.get_requests())

    assert [
        ("langchain.llm.start", mock_trace_id),
        ("langchain.llm.end", mock_trace_id),
        ("my.custom.event", mock_trace_id),
    ] == [(req["message"], req["traceId"]) for req in requests]


def test_callback_with_agent_and_tools(httpx, handler):
    llm = OpenAI(temperature=0)
    llm_math_chain = LLMMathChain.from_llm(llm)
    tools = [
        Tool.from_function(
            func=llm_math_chain.run,
            name="Calculator",
            description="useful for when you need to answer questions about math",
        )
    ]
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
    agent.run("What is 2+2?", callbacks=[handler])

    requests = decode_requests(httpx.get_requests())

    messages = [req["message"] for req in requests]
    trace_ids = [req["traceId"] for req in requests]

    assert messages == [
        "langchain.chain.start",
        "langchain.chain.start",
        "langchain.llm.start",
        "langchain.llm.end",
        "langchain.chain.end",
        "langchain.agent.action",
        "langchain.tool.start",
        "langchain.chain.start",
        "langchain.chain.start",
        "langchain.llm.start",
        "langchain.llm.end",
        "langchain.chain.end",
        "langchain.chain.end",
        "langchain.tool.end",
        "langchain.chain.start",
        "langchain.llm.start",
        "langchain.llm.end",
        "langchain.chain.end",
        "langchain.agent.finish",
        "langchain.chain.end",
    ]

    # All trace_ids should be the same and should not be None
    assert trace_ids[0] is not None
    assert len(set(trace_ids)) == 1
