from langchain.agents import AgentType
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain
from langchain.llms import OpenAI
from langchain.tools import Tool

from autoblocks.vendor.langchain import AutoblocksCallbackHandler


def test_callback_handler():
    events = []
    handler = AutoblocksCallbackHandler("mock-key")
    handler._ab.send_event = lambda message, trace_id, **kwargs: events.append((message, trace_id))

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

    messages = [event[0] for event in events]
    trace_ids = [event[1] for event in events]

    assert messages == [
        "langchain.agents.agent.AgentExecutor.start",
        "langchain.chains.llm.LLMChain.start",
        "langchain.llms.openai.OpenAI.start",
        "langchain.llms.openai.OpenAI.end",
        "langchain.chains.llm.LLMChain.end",
        "langchain.agent.action",
        "langchain.tool.Calculator.start",
        "langchain.chains.llm_math.base.LLMMathChain.start",
        "langchain.chains.llm.LLMChain.start",
        "langchain.llms.openai.OpenAI.start",
        "langchain.llms.openai.OpenAI.end",
        "langchain.chains.llm.LLMChain.end",
        "langchain.chains.llm_math.base.LLMMathChain.end",
        "langchain.tool.Calculator.end",
        "langchain.chains.llm.LLMChain.start",
        "langchain.llms.openai.OpenAI.start",
        "langchain.llms.openai.OpenAI.end",
        "langchain.chains.llm.LLMChain.end",
        "langchain.agent.finish",
        "langchain.agents.agent.AgentExecutor.end",
    ]

    # All trace_ids should be the same and should not be None
    assert trace_ids[0] is not None
    assert len(set(trace_ids)) == 1
