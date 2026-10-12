"""N06：Reducer。两个节点提交局部 scores 更新。"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class CheckState(TypedDict):
    scores: Annotated[list[int], operator.add]


def first_check(state: CheckState):
    return {"scores": [70]}


def second_check(state: CheckState):
    return {"scores": [90]}


def main():
    builder = StateGraph(CheckState)
    builder.add_node("first", first_check)
    builder.add_node("second", second_check)
    builder.add_edge(START, "first")
    builder.add_edge("first", "second")
    builder.add_edge("second", END)

    graph = builder.compile()
    result = graph.invoke({"scores": []})
    assert result["scores"] == [70, 90]
    print("最终结果:", result)


if __name__ == "__main__":
    main()
