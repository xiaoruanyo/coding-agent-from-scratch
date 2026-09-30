# 04. State、Checkpoint 与 Memory：Agent 到底“记住”什么

## 1. Agent State 不只有 messages

最初我们可以只有：

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

Coding Agent 很快还需要：

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    test_passed: bool
    last_error: str
    last_error_type: str
```

## 2. messages 与结构化 State

`messages` 更适合：

```text
用户说了什么
LLM 做过哪些决定
调用过哪些 Tool
Tool 返回什么
```

结构化 State 更适合：

```text
测试是否通过
失败几次
错误类型
Graph 必须精确判断的事实
```

核心：

> 只是给 LLM 参考的信息，不一定要再复制进 State。

## 3. ToolMessage 不会自动更新自定义 State

Tool 返回：

```python
{"passed": False, "output": "..."}
```

通常会先变成 ToolMessage。

它不会因为返回 dict 就自动让：

```python
state["test_passed"]
```

变化。

我们的 Coding Agent 选择了一层：

```text
ToolMessage(run_test)
↓
sync_state_node
↓
test_passed / retry_count / last_error
```

这是主动设计的“Tool 结果 → Graph State”转换层。

## 4. Checkpoint

最小：

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

调用时：

```python
config = {
    "configurable": {
        "thread_id": "task_001"
    }
}
```

Checkpoint 解决：

> 当前这条任务执行到哪里了？

同一个 Graph 可以被多个 thread 使用，而 State 按 `thread_id` 隔离。

## 5. Checkpoint 不等于 Memory

```text
Checkpoint
→ 当前 thread 的工作现场

Memory
→ 跨 thread / 跨任务仍值得保留的信息
```

例如：

```text
这次任务测试失败了两次
→ 当前 State / Checkpoint

这个项目统一使用 pytest
→ 长期 Memory 候选
```

## 6. Store

学习版：

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
```

可以按 namespace 隔离：

```python
namespace = ("memories", "user_123")
```

典型维度：

```text
thread_id
→ 一条任务 / 会话

user_id / namespace
→ 长期信息属于谁
```

## 7. Memory Tool

Memory 也可以通过 Tool Calling 让模型自己搜索或写入。

本质仍是：

```text
LLM
↓
tool_call
↓
Memory Tool
↓
Store
```

不是一个完全不同的 Agent 机制。

## 8. Checkpoint 与 Context 也不是一回事

即使 Checkpoint 保存了 10 万 token 的 messages，

如果下一轮仍然：

```python
model.invoke(state["messages"])
```

模型还是会收到 10 万 token。

所以：

```text
Checkpoint
→ 保存现场

Context Engineering
→ 决定当前模型看到什么
```

后者在第 11 章展开。

## 9. 核心

```text
messages
→ LLM 工作历史

Structured State
→ 程序精确使用的状态

Checkpoint
→ 当前任务可恢复现场

Memory
→ 跨任务长期信息
```
