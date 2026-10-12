"""N05：条件边与循环。模拟第一次 70 分、第二次 90 分。"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ArticleState(TypedDict):
    article: str
    score: int
    check_count: int


def check_article(state: ArticleState):
    count = state["check_count"] + 1
    score = 70 if count == 1 else 90
    print(f"第 {count} 次检查，评分：{score}")
    return {"check_count": count, "score": score}


def rewrite_article(state: ArticleState):
    print("重新写文章")
    return {"article": "这是重写后的文章"}


def route_article(state: ArticleState):
    return "pass" if state["score"] >= 80 else "rewrite"


def main():
    builder = StateGraph(ArticleState)
    builder.add_node("check", check_article)
    builder.add_node("rewrite", rewrite_article)

    builder.add_edge(START, "check")
    builder.add_conditional_edges(
        "check",
        route_article,
        {"pass": END, "rewrite": "rewrite"},
    )
    builder.add_edge("rewrite", "check")

    graph = builder.compile()
    result = graph.invoke(
        {"article": "原始文章", "score": 0, "check_count": 0}
    )

    assert result["score"] == 90
    assert result["check_count"] == 2
    print("最终结果:", result)


if __name__ == "__main__":
    main()
