import json
import os
from unittest import mock

from langchain.agents import AgentType
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain
from langchain.llms import OpenAI
from langchain.tools import Tool

from autoblocks._impl.config.constants import AUTOBLOCKS_INGESTION_KEY
from autoblocks.vendor.langchain import AutoblocksCallbackHandler

# Tests that we're sending the current langchain version.
# Should update this whenever we update the version in pyproject.toml.
CURRENT_LANGCHAIN_VERSION = "0.0.316"


def decode_requests(requests):
    return [json.loads(req.content.decode()) for req in requests]


def test_callback_handler(httpx_mock):
    httpx_mock.add_response(json=dict(traceId="mock-trace-id"))

    with mock.patch.dict(os.environ, {AUTOBLOCKS_INGESTION_KEY: "mock-ingestion-key"}):
        handler = AutoblocksCallbackHandler()

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

    requests = decode_requests(httpx_mock.get_requests())

    messages = [req["message"] for req in requests]
    trace_ids = [req["traceId"] for req in requests]
    property_payloads = [req["properties"] for req in requests]

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

    for payload in property_payloads:
        assert payload["__langchainVersion"] == CURRENT_LANGCHAIN_VERSION
        assert payload["__langchainLanguage"] == "python"
