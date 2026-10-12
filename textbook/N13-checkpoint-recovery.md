# N13｜Checkpoint：Agent 暂停之后，谁保存工作现场？

> **要解决的问题**：Agent 已经提出文件修改、等待用户在浏览器批准。如果用户一分钟后才回复，后端如何恢复正确的位置？为什么有对话历史还不够？

## 1. 从一次真正的任务开始

假设 Agent 已经搜索了 `src/calculator.py`，读懂了错误，提出修改：

```text
main.py:
- return a - b
+ return a + b
```

此刻的 Graph 必须暂停，直到人批准或者拒绝。

问题不是“让 LLM 记住刚才的对话”那么简单。系统还要知道：

- 当前任务属于哪一个用户请求；
- 正在等待哪一次具体的审批；
- 运行到图的哪一步；
- State 里已经积累的事实是什么；
- 恢复时应该继续哪条任务，不能恢复到别的任务；
- 如何避免重复执行此前已经发生的文件副作用。

## 2. 三个经常混在一起的概念

| 机制 | 解决的问题 | 通常保存什么 |
|---|---|---|
| Messages | 本次模型调用需要哪些消息上下文 | HumanMessage、AIMessage、ToolMessage |
| Checkpoint | 某个 Graph thread 的可恢复执行现场 | State 快照、执行进度、等待事项 |
| 长期 Memory / Store | 跨多次任务能复用哪些经验 | 经核验的项目规范、稳定偏好 |

Checkpoint 不等于每次把全部历史发给模型。一个 Graph 线程可以有很多检查点，但 Context Builder 仍然应该只挑选当前模型真正需要的信息。

## 3. 最小离线实验

本实验不需要模型 API：

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict):
    count: int

def increment(state: State):
    return {"count": state["count"] + 1}

builder = StateGraph(State)
builder.add_node("increment", increment)
builder.add_edge(START, "increment")
builder.add_edge("increment", END)

graph = builder.compile(checkpointer=InMemorySaver())

config_a = {"configurable": {"thread_id": "task-a"}}
config_b = {"configurable": {"thread_id": "task-b"}}

print(graph.invoke({"count": 0}, config=config_a))
print(graph.invoke({"count": 10}, config=config_b))
print(graph.get_state(config_a).values)
print(graph.get_state(config_b).values)
```

观察：两条 thread 各有自己的检查点与 State。它们不会因为使用同一个 compiled graph 就自动共享执行进度。

`thread_id` 是存取检查点的关键，而不是系统帮你猜测的“当前任务”。正式产品要把 UI 的 task_id 和 Graph 的 thread_id 做可靠的关联。

### 为什么不是简单存一个 dict？

保存普通 dict 可以保存数据，却不代表框架知道暂停位置、待执行任务和恢复语义。Checkpointer 要与 LangGraph Runtime 协作。

## 4. 中断与恢复的两个关键 API

在需要人工参与的 Node 中：

```python
from langgraph.types import interrupt

def approval_node(state):
    decision = interrupt({
        "kind": "file_write",
        "path": "main.py",
        "question": "批准这次具体修改吗？",
    })
    return {"approved": bool(decision)}
```

此时 Graph 暂停，调用方能得到中断信息；Runner/UI 展示审批详情。之后：

```python
from langgraph.types import Command

graph.invoke(
    Command(resume=True),
    config={"configurable": {"thread_id": "task-001"}},
)
```

以上是展示机制的**局部片段**，不是从零完整可运行的图。正确运行必须先用该 thread_id 启动并暂停图，而且 compile 时启用 checkpointer。

如果用户明确拒绝，就传入适当的拒绝值；业务逻辑必须确保写入工具不会因此执行。

## 5. 最容易忽略的工程问题：Node 恢复时可能重放

直觉可能以为：

```text
执行函数前半段 → interrupt
                   ↓
                 暂停
                   ↓
         从 interrupt 下一行继续
```

但 LangGraph 的中断恢复会从被中断节点的开头重新执行前置代码，并在 `interrupt` 恢复点接收 resume 值。

因此下面的顺序是错的：

```python
def approval_node(state):
    actually_write_file()         # 已发生副作用！
    decision = interrupt({...})   # 才问用户
```

正确应当是：

```text
构造并固定修改提案（无写入）
        ↓
approval_gate / interrupt
        ↓
用户批准具体提案
        ↓
tools（只执行已批准且再次校验过的提案）
```

即使审批 Node 无副作用，执行 Node 的重复调用风险仍要考虑：精确旧文本校验、工具操作 ID、文件版本核验、原子写入等机制不能省略。

## 6. InMemorySaver 的能力边界

`InMemorySaver` 很适合课堂和调试，但它只把检查点放在进程内存中。

不要因此承诺：

- 关闭 Python 后端之后依然能恢复所有暂停任务；
- 多个 Uvicorn worker 之间天然共享检查点；
- 崩溃后文件操作会自动回滚；
- 任何人只要知道 task_id 就可以恢复别人的任务。

完整产品的恢复能力需要持久化 Checkpointer、任务存储、身份与权限校验，并做真实的重启恢复测试。教学阶段可以先用内存版本理解，再升级至适合本地应用的持久化实现。

## 7. 两条恢复链路

**Graph 级恢复：**

```text
同一 thread_id
→ Command(resume=审批结果)
→ 运行被暂停的 Graph
```

**产品级恢复：**

```text
用户在浏览器打开 task_id
→ FastAPI 查询任务记录
→ 找到对应 thread_id 和待审批请求
→ 用户提交对该请求的决定
→ 后端授权并恢复 Graph
→ 向前端继续发送进度事件
```

Graph 的 Checkpointer 并不自动帮 FastAPI 做任务列表、事件流和用户权限。

## 8. 这些东西都不属于 Checkpoint 的职责

- 决定要读哪个文件：LLM 的动态选择。
- 读文件时不许越界：工具的能力边界。
- 当前模型应该看到多少旧消息：Context Builder。
- 跨多次任务复用项目规范：长期 Memory。
- 测试之后代码是否又修改：文件/状态同步规则。
- UI 刷新后怎样显示完整时间线：任务事件存储与前端。

所以“有 Checkpoint”绝不能替代整套 Harness。

## 9. 与最终产品如何连接

审批前暂停：`approval_gate` Node。  
保存现场：Checkpointer。  
用户交互：React。  
请求与恢复：FastAPI Runner。  
实际执行：受控 Tool。  
结果与最终报告：`sync_state`、`completion_guard`、任务事件流。

这一章对应前端的一个具体行为：**“待批准”页面可以来自真正暂停的 Agent，而不是前端假造了一个等待状态。**

## 10. 理解检查

1. 为什么 `messages` 里保留原来对话不等于能恢复 Graph？
2. 为什么 `thread_id` 不能在恢复时随便换？
3. 为什么 `interrupt` 前不能发生不可重复的写入副作用？
4. 为什么 InMemorySaver 不满足“后端重启后继续任务”的产品要求？
5. UI 的 task_id 与 Graph 的 thread_id 是同一个概念吗？

请带着这些问题继续下一课：真实工作区的工具边界与精确文件修改。
