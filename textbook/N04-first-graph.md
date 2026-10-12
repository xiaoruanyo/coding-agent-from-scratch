# N04｜第一次 LangGraph：State、Node、Edge 都在做什么？

> 前置：理解 N03 的 Messages。本课不需要模型 API Key；先用纯 Python 节点掌握 Graph 的执行规律。**这比直接把 LLM、Tool 和审批都塞在一个例子里更容易排错。**

## 1. 为什么我们需要一张 Graph？

普通代码可以串行调用：

```python
outline = create_outline(topic)
article = write_article(outline)
```

如果只有这两步，未必需要 LangGraph。

但当需求变成：

```text
生成文章
   ↓
检查评分
   ├─ 合格 → 结束
   └─ 不合格 → 重写 → 再检查
```

流程就开始出现分支、回跳与共享状态。

Coding Agent 会更加复杂：

```text
LLM → 提出工具调用 → 审批 → 工具执行 → 更新事实
 ▲                                             │
 └──────────── 测试失败，继续分析 ─────────────┘
```

Graph 的价值不是代替 Python 写 `if`，而是把这些步骤、流向和状态更新表达得清楚，便于观察、修改和恢复。

## 2. State：这张图里的公共工作数据

假设我们写一篇文章：

```python
from typing import TypedDict

class ArticleState(TypedDict):
    topic: str
    outline: str
    article: str
```

`TypedDict` 描述了 State 有哪些键，以及它们预期是什么类型。

它**不会自动创建字段，也不会给字段赋初值**。

如果你执行：

```python
state = {"topic": "LangGraph"}
print(state["outline"])
```

在 Python 层会遇到 `KeyError`，因为字典没有 `outline` 这个键。

实际输入是否需要提供每个字段，取决于后续节点如何读取它们，以及你是否把某些字段设计为可选；不要把 `TypedDict` 当成自动初始化器。

## 3. Node：负责做一件事的函数

两个最小 Node：

```python
def create_outline(state: ArticleState):
    topic = state["topic"]
    return {
        "outline": f"文章提纲：1. 什么是{topic}；2. 为什么使用它"
    }

def write_article(state: ArticleState):
    return {
        "article": f"根据提纲写正文：{state['outline']}"
    }
```

注意返回值：

```python
return {"outline": "..."}
```

不是把原来的整个 `state` 全部返回，而是只交回该 Node 更新的字段。

LangGraph 会根据相应的 State channel 规则合并更新。对于这里普通的字段，后一次更新通常覆盖之前的值；将来我们用 Reducer 改变某些字段的合并方式。

### Node 不是 Tool

Node 是 Graph 固定调度的一步；Tool 是模型可以选择请求的外部能力。

例如：

- “每次执行完 pytest 必须整理测试状态”可以是固定 Node。
- “应该读取哪个文件”可以由模型决定，通过 `read_file` Tool 来做。

同一个操作是否要成为 Node，取决于谁控制它的执行时机，而不是函数名称。

## 4. Edge：下一步走向哪里

看一个完整的最小例子：

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

class ArticleState(TypedDict):
    topic: str
    outline: str
    article: str

def create_outline(state: ArticleState):
    return {
        "outline": f"提纲：介绍{state['topic']}；解释价值"
    }

def write_article(state: ArticleState):
    return {
        "article": f"正文：{state['outline']}"
    }

builder = StateGraph(ArticleState)

builder.add_node("create", create_outline)
builder.add_node("writer", write_article)

builder.add_edge(START, "create")
builder.add_edge("create", "writer")
builder.add_edge("writer", END)

graph = builder.compile()

result = graph.invoke({
    "topic": "LangGraph",
    "outline": "",
    "article": "",
})

print(result)
```

这个示例完全不需要 LLM，因此本课可以离线验证。

### 逐行拆解 Graph Builder

`builder = StateGraph(ArticleState)`：声明图使用怎样的 State schema。

`add_node("create", create_outline)`：注册一个名叫 `create` 的 Node，关联到 Python 函数 `create_outline`。

**第一个参数是图里的节点名，第二个参数是函数对象**。写成 `create_outline()` 就是在构建图时立刻调用函数，通常不是你想要的行为。

`add_edge(START, "create")`：从图入口进入 `create`。

`add_edge("create", "writer")`：完成提纲之后执行正文节点。

`add_edge("writer", END)`：正文节点结束后，流程终止。

`compile()`：把 builder 编译为可执行图。

`graph.invoke({...})`：用一份初始 State 触发图的执行。

## 5. `set_entry_point` 与 START 是什么关系？

你曾经问过：“为什么 set_entry_point 没有显式 add_edge(start, ...)？”

这是两种表达入口的方式：

```python
builder.set_entry_point("create")
```

与：

```python
builder.add_edge(START, "create")
```

在这个简单场景里都表达“从 create 开始”，不要为了看起来完整而额外发明一个无事可做的 `start` Node。

## 6. 运行时 State 如何变化？

你可以暂时把执行过程想成：

```text
初始 State：
topic = "LangGraph"
outline = ""
article = ""
       │
       ▼
create_outline
返回 {"outline": "提纲：介绍 LangGraph；解释价值"}
       │
       ▼
Runtime 合并 State：
topic = "LangGraph"
outline = "提纲：介绍 LangGraph；解释价值"
article = ""
       │
       ▼
write_article
返回 {"article": "正文：提纲：介绍 LangGraph；解释价值"}
       │
       ▼
最后 State 有三个字段
```

重点不是字符串写得好不好，而是理解**节点可以看到此前步骤已经产生的数据**。

你可以在两个节点内部加入：

```python
print("create 收到:", state)
print("writer 收到:", state)
```

真实运行一次，就能观察哪些字段在哪一步发生变化。

## 7. 初学者的三个典型错误

### `compile` 被写成 `compiled`

```python
graph = builder.compile()  # 正确 API 名称
```

不要凭英文直觉猜 API；遇到 `AttributeError` 先检查拼写和当前版本文档。

### 把 Node 函数调用结果传给 `add_node`

```python
builder.add_node("create", create_outline())  # 通常错误
builder.add_node("create", create_outline)    # 函数引用
```

括号 `()` 代表在这里执行函数；不带括号才是把函数对象交给框架以后调用。

### State 中缺少 Node 必须读取的字段

```python
def create_outline(state):
    print(state["topic"])
```

如果调用入口没给 `topic`，也没有上游步骤提供它，就会失败。具体 API 层可能有不同包装异常，但根本原因仍是字段未就绪。

## 8. State 不只有 messages

刚才 `ArticleState` 只有 `topic`、`outline` 和 `article`，没有 `messages`，照样是一张合法的图。

LangGraph 的 State 不是“只能用 Messages 的容器”。

以后我们会定义：

```python
class CodingAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    test_passed: bool
```

原因是 Coding Agent 既需要模型交互历史，也需要程序精确使用的控制状态。

## 9. 为什么不把整个业务逻辑都放在一个 Node？

技术上你完全可以这样写：

```python
def everything(state):
    # 生成文章
    # 检查
    # 重写
    # 再检查
    ...
```

但分开有两个好处：

- **职责更清楚**：哪一步生成内容，哪一步检查结果，一眼能看出来。
- **控制更灵活**：以后给检查步骤添加不同的路由、观测或重试策略时不必拆一个巨函数。

反过来也要注意，Node 不是越多越好。如果一个 Node 内只是三行纯 Python 字符串处理，不涉及独立控制，就不一定值得拆成三层 Graph。

## 10. 本课理解检查

1. `TypedDict` 会自动生成 `outline=""` 吗？
2. 为什么 Node 通常只返回局部 State 更新？
3. `create_outline` 和 `create_outline()` 在注册 Node 时有什么差别？
4. `compile()` 和 `invoke()` 分别发生在什么阶段？
5. 为什么并不是每个 Python 函数都需要成为 Node？

下一课：[N05｜条件边与循环](N05-conditional-loop.md)。
