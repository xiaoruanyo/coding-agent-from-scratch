"""N04：第一张图。无需 LLM / API Key。"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ArticleState(TypedDict):
    topic: str
    outline: str
    article: str


def create_outline(state: ArticleState):
    print("create 收到:", state)
    return {"outline": f"提纲：介绍{state['topic']}；解释价值"}


def write_article(state: ArticleState):
    print("writer 收到:", state)
    return {"article": f"正文：{state['outline']}"}


def main():
    builder = StateGraph(ArticleState)
    builder.add_node("create", create_outline)
    builder.add_node("writer", write_article)

    builder.add_edge(START, "create")
    builder.add_edge("create", "writer")
    builder.add_edge("writer", END)

    graph = builder.compile()
    result = graph.invoke({"topic": "LangGraph", "outline": "", "article": ""})

    assert "LangGraph" in result["article"]
    print("最终结果:", result)


if __name__ == "__main__":
    main()
