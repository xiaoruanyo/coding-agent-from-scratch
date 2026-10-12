# N06｜Reducer：为什么要设计“状态合并规则”？

> 本课解决一个实际困惑：我已经有 State，为什么还要 Reducer？如果只是多次写一个字段，直接赋值不就够了吗？

## 1. 从最熟悉的 State 更新开始

上一课里我们有：

```python
class ArticleState(TypedDict):
    score: int
    check_count: int
```

第一次 check 返回：

```python
{"score": 70, "check_count": 1}
```

第二次 check 返回：

```python
{"score": 90, "check_count": 2}
```

我们的预期很自然：新值覆盖旧值。

```text
score: 70 → 90
check_count: 1 → 2
```

所以对于 `score`、`test_passed`、`last_error_type` 这样的字段，使用覆盖更新通常合理。

但如果要保存“历史检查结果”，情况就不同了。

## 2. 同样的更新方式，在历史列表上出了问题

假设 State 改成：

```python
from typing import TypedDict

class CheckState(TypedDict):
    scores: list[int]
```

第一个节点返回：

```python
{"scores": [70]}
```

第二个节点返回：

```python
{"scores": [90]}
```

如果字段采用默认覆盖语义，最后只能得到：

```python
{"scores": [90]}
```

但业务可能希望：

```python
{"scores": [70, 90]}
```

这时不能再使用“新列表覆盖旧列表”，而要定义**如何合并旧值和新值**。

这就是 Reducer（归约/合并函数）出现的原因。

注意，如果 Node 自己读取当前历史并返回整个新列表，在简单串行场景下也能实现累积。但当多个分支并行更新同一个字段时，仅靠节点自己拼列表会遇到并发更新语义问题。Reducer 把合并规则交给 State Channel，才更清晰。

## 3. 用最小例子理解 Reducer

```python
from typing import Annotated, TypedDict
import operator

class CheckState(TypedDict):
    scores: Annotated[list[int], operator.add]
```

先只看一行：

```python
scores: Annotated[list[int], operator.add]
```

它告诉 LangGraph：

- 这个字段的类型是 `list[int]`；
- 当新节点提交 `scores` 更新时，使用 `operator.add` 作为合并规则。

对于列表：

```python
[70] + [90]  # [70, 90]
```

因此两个节点各返回一个元素的列表时，State 可以保存两次结果。

## 4. 一段完整离线示例

```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

class CheckState(TypedDict):
    scores: Annotated[list[int], operator.add]

def first_check(state: CheckState):
    return {"scores": [70]}

def second_check(state: CheckState):
    return {"scores": [90]}

builder = StateGraph(CheckState)
builder.add_node("first", first_check)
builder.add_node("second", second_check)

builder.add_edge(START, "first")
builder.add_edge("first", "second")
builder.add_edge("second", END)

graph = builder.compile()

print(graph.invoke({"scores": []}))
```

预期最终状态：

```python
{"scores": [70, 90]}
```

这个示例的重点不是两个分数本身，而是：**同样是节点返回 `{"scores": [90]}`，有 Reducer 时含义是“追加更新”；没有时通常是“覆盖旧值”。**

## 5. Reducer 究竟放在哪里？

不是在每个 Node 里调用：

```python
operator.add(...)
```

而是定义在 State schema 上：

```python
scores: Annotated[list[int], operator.add]
```

Node 仍然只返回自己产生的局部更新：

```python
return {"scores": [90]}
```

这样节点不需要知道“过去所有分数是什么”，合并策略与具体业务计算分离。

## 6. 最有价值的场景：并行节点

假设两个节点同时读到同一个 State：

```text
           START
          /     \
     node_A     node_B
          \     /
           汇合
```

它们都要更新 `evidence`：

```python
def node_a(state):
    return {"evidence": ["发现函数 calculate_total"]}

def node_b(state):
    return {"evidence": ["发现测试 test_total"]}
```

如果这个字段没有合适的合并策略，同一个执行步骤中有多个更新就可能发生写入冲突，而不是自动猜“两个字符串应该怎样合并”。

我们明确写：

```python
class SearchState(TypedDict):
    evidence: Annotated[list[str], operator.add]
```

就表达了“把两路证据合并为列表”的业务意图。

**但要注意：并行执行的返回先后顺序，不应该被当成业务正确性前提。** 即使采用列表合并，也不要假设独立并行分支的内容始终以固定顺序排列。

例如，展示给模型之前可以按来源路径或工具 ID 明确排序；若结果只需要“有哪些证据”，应避免依赖顺序。

## 7. Reducer 不是只有列表加法

Reducer 本质上是一个形如：

```python
def reducer(old_value, update_value):
    return merged_value
```

的合并函数。

例如使用整数计数时可以有加法语义：

```python
from typing import Annotated

count: Annotated[int, operator.add]
```

但这时 Node 返回的值代表**增量**，不是新的总数。

如果当前计数为 2：

```python
return {"count": 1}
```

加法合并结果为 3。

若你误以为它是覆盖，返回总数 3，就会合并为 5。这是初学者很常见的陷阱。

**一个字段到底是“快照”还是“增量”，要由设计明确规定。**

对于 Coding Agent 的 `retry_count`，我们的 V1 可以采用普通覆盖字段，再由单一 `sync_state` Node 计算新的绝对次数，以减少不必要的语义复杂度；没有必要凡是计数都配 Reducer。

## 8. 为什么 Messages 要使用特殊的 `add_messages`？

Coding Agent 常见写法：

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

直觉上它和“累积列表”类似，但它不仅仅等于 `operator.add`。

`add_messages` 会依据消息的 ID 处理合并，允许添加新消息，并在特定情况下用相同 ID 的新消息替换旧消息。它适合 LangGraph 的消息状态管理。

所以不要随意把：

```python
messages: Annotated[list, add_messages]
```

改成：

```python
messages: Annotated[list, operator.add]
```

然后假设所有行为都一样。

### `add_messages` 的一个关键理解

节点返回：

```python
return {"messages": [response]}
```

一般表示“把新的消息更新交给合并机制”，而不是要求节点每次复制并返回完整历史。

这减少了多节点下消息合并的复杂度。

## 9. 三个容易误解的地方

**误解一：Reducer 等于 reduce 迭代器。**

名称相似，但我们这里具体讨论的是 LangGraph State Channel 的更新合并规则。你可以把它理解为“多个更新怎么形成一个状态”，不要自动套入大数据批处理 API 的每一项语义。

**误解二：所有字段都应该用 Reducer。**

不是。像 `test_passed`、`last_error_type`，通常需要以最新事实覆盖；用列表追加反而会让后续判断复杂。

**误解三：有 Reducer 就能避免所有并发问题。**

不是。Reducer 解决的是 State 更新合并的语义问题。它不能保证并行写文件的原子性，也不能自动解决跨文件工具操作顺序、重复执行或幂等问题。

## 10. 小练习：字段应该覆盖还是累积？

考虑以下字段：

| 字段 | 推荐初始策略 | 理由 |
|---|---|---|
| `test_passed` | 覆盖 | 要表达最近一次有效测试的事实 |
| `last_error_type` | 覆盖 | 当前错误类型 |
| `retry_count` | V1 单写入者覆盖 | `sync_state` 可以明确计算总次数 |
| `messages` | `add_messages` | 保存模型与 Tool 对话更新 |
| `evidence` | 视用途可列表合并 | 多路独立检索证据需要汇集 |
| `working_summary` | 覆盖 | 新摘要代表当前压缩工作现场 |

这里没有一种规则适合所有字段。

## 11. 真正的理解检查

1. 两个节点分别返回 `{"scores": [70]}` 与 `{"scores": [90]}`，为什么没有 Reducer 不一定能得到两个分数？
2. 使用 `operator.add` 后，节点返回的是全量还是增量？
3. `messages` 为什么推荐 `add_messages`，而不随意使用 `operator.add`？
4. Reducer 能保证文件修改的副作用只发生一次吗？
5. 为什么我们的 V1 `retry_count` 可以先不使用 Reducer？

**下一课：** [N07｜第一次 Tool Calling](N07-tool-calling.md)。
