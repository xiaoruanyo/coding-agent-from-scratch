"""N07-N08：最小 ToolNode / Agent Loop；需要真实模型 API。"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


@tool
def add(a: int, b: int) -> int:
    """计算两个整数之和。"""
    return a + b


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def main():
    load_dotenv()
    key = os.getenv("DEEPSEEK_API_KEY")
    model_name = os.getenv("DEEPSEEK_MODEL")
    if not key or not model_name:
        raise RuntimeError("请先配置 DEEPSEEK_API_KEY 和 DEEPSEEK_MODEL")

    model = ChatOpenAI(
        model=model_name,
        api_key=key,
        base_url="https://api.deepseek.com",
    )
    tools = [add]
    with_tools = model.bind_tools(tools)

    def chat(state: AgentState):
        response = with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def route(state: AgentState):
        last = state["messages"][-1]
        return "tools" if last.tool_calls else "finish"

    builder = StateGraph(AgentState)
    builder.add_node("chat", chat)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "chat")
    builder.add_conditional_edges(
        "chat", route, {"tools": "tools", "finish": END}
    )
    builder.add_edge("tools", "chat")
    graph = builder.compile()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="请使用 add 工具计算 123 + 456，然后告诉我结果")
            ]
        },
        config={"recursion_limit": 15},
    )
    for message in result["messages"]:
        print(type(message).__name__, ":", message.content)


if __name__ == "__main__":
    main()
