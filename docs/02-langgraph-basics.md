# 02. LangGraph 基础：State、Node、Edge、Loop

## 1. 为什么需要 Graph

普通代码当然可以写：

```python
if ...
    ...
else:
    ...
```

但 Agent 很快会出现：

```text
A → B → C → B → D
```

也就是：

- 条件分支；
- 循环；
- 回跳；
- 多步骤共享数据；
- 中断与恢复。

Graph 的价值是让这些流程结构显式化。

## 2. State

State 是 Graph 执行过程中共享的数据。

```python
from typing import TypedDict

class ArticleState(TypedDict):
    article: str
    score: int
    check_count: int
```

注意：

> `TypedDict` 只定义结构和类型提示，不会自动给字段初始化。

如果 Node 里读取：

```python
state["check_count"]
```

那么输入 State 中必须已有这个字段，或者之前的 Node 已经写入。

## 3. Node

Node 就是“一步工作”。

```python
def write_article(state):
    return {
        "article": "..."
    }
```

Node 返回的通常是 Partial State Update：

```text
输入完整 State
↓
Node 只返回自己修改的字段
↓
Runtime 合并回 State
```

## 4. Edge

Edge 决定流程下一步。

```python
builder.add_edge("create", "writer")
```

## 5. Entry / START / END

最小 Graph：

```python
from langgraph.graph import StateGraph
from langgraph.constants import END

builder = StateGraph(ArticleState)
builder.add_node("writer", write_article)
builder.set_entry_point("writer")
builder.add_edge("writer", END)

graph = builder.compile()
```

`set_entry_point()` 就是在告诉 Graph 从哪个 Node 开始，所以不需要自己再造一个假的 start Node。

## 6. Conditional Edge

例如文章评分：

```python
def route_article(state):
    if state["score"] >= 80:
        return "pass"
    return "rewrite"

builder.add_conditional_edges(
    "check",
    route_article,
    {
        "pass": END,
        "rewrite": "rewrite",
    },
)
```

记住：

```text
路由函数返回标签
↓
mapping
↓
目标 Node / END
```

传的是函数：

```python
route_article
```

不是调用结果：

```python
route_article()
```

## 7. Loop

例如：

```text
check
↓
不通过
↓
rewrite
↓
check
```

代码：

```python
builder.add_edge("rewrite", "check")
```

Loop 必须有退出条件，否则可能无限执行。

## 8. Reducer

普通字段更新：

```text
旧值
↓
新值覆盖
```

Reducer 则规定：

```text
旧值 + 新值
↓
按规则合并
```

后面并行执行时，如果多个分支同时写同一个字段，Reducer 就非常重要。

## 9. add_messages

Agent 最常见：

```python
from typing import Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

`add_messages` 是专门为消息列表设计的 Reducer。

## 10. 最早的“检查—重写”练习

我们曾用：

```text
score < 80
→ rewrite
→ 再 check

score >= 80
→ END
```

以及：

```text
第 1 次检查：70
第 2 次检查：90
```

来理解：

- State 如何跨 Node 更新；
- Conditional Edge 如何路由；
- Loop 如何回到之前的 Node；
- `check_count` 为什么必须初始化。

## 11. 本章核心

```text
State
→ 数据

Node
→ 做事

Edge
→ 下一步

Conditional Edge
→ 根据状态选下一步

Loop
→ 回到之前的步骤

Reducer
→ 多个更新如何合并
```
