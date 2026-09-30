# Coding Agent 中文速查

> 只保留核心概念、常用 API 和架构判断。用于复习与查询，不替代正文。

## LangGraph 基础

```python
from langgraph.graph import StateGraph
from langgraph.constants import START, END
```

```text
State → 跨步骤共享数据
Node  → 一步工作
Edge  → 下一步
Conditional Edge → 条件路由
Loop  → 回到之前步骤
Reducer → 同一字段的新旧更新如何合并
```

常用：

```python
builder = StateGraph(MyState)
builder.add_node("a", node_a)
builder.set_entry_point("a")
builder.add_edge("a", END)
builder.add_conditional_edges(...)
graph = builder.compile()
graph.invoke({...})
```

---

## Messages

```python
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
```

```text
HumanMessage → 用户
AIMessage → 模型
SystemMessage → 系统规则
ToolMessage → Tool 执行结果
```

---

## Tool Calling

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    return a + b
```

```python
model_with_tools = model.bind_tools(tools)
```

```text
@tool → 定义 Tool
bind_tools → 告诉 LLM 可用 Tool
tool_calls → LLM 提出调用意图
ToolNode → 真正执行 Tool
ToolMessage → 把结果送回 LLM
```

一个 AIMessage 可以有多个 tool_calls。

```text
无依赖 → 可并行
有依赖 → LLM → Tool → 结果 → LLM → 下一 Tool
```

---

## ToolNode

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools)
builder.add_node("tools", tool_node)
```

---

## Agent State

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    test_passed: bool
    last_error: str
    last_error_type: str
```

判断字段是否进 State：

```text
Graph / Node 后面真要结构化读取？
跨步骤仍有意义？
语义明确稳定？
messages 已经够不够？
```

State 不是 Agent 日志。

---

## Checkpoint

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
app = builder.compile(checkpointer=checkpointer)
```

```python
config = {
    "configurable": {
        "thread_id": "task-001"
    }
}
```

```text
Checkpoint → 当前 thread 工作现场
Memory → 跨任务长期信息
```

---

## Memory / Store

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
```

```text
thread_id → Checkpoint 维度
namespace / user_id → Memory 维度
```

---

## Human-in-the-loop

```python
from langgraph.types import interrupt, Command
```

暂停：

```python
approved = interrupt({...})
```

恢复：

```python
Command(resume=True)
```

必须使用同一个 thread_id。

> interrupt 前不要做不可重复副作用。

---

## Command

```text
Command.update → 更新 State
Command.goto   → 指定下一 Node
Command.resume → 恢复 interrupt
```

---

## Subgraph

```python
subgraph = sub_builder.compile()
parent_builder.add_node("sub_flow", subgraph)
```

```text
同名 + 同语义 + 同类型 → 可共享 State channel
需要转换 → 显式 Adapter
```

---

## Parallel / Send

```python
from langgraph.types import Send
```

```python
return [
    Send("analyze_file", {"file": f})
    for f in state["files"]
]
```

同一 Superstep 多分支写同字段时需要 Reducer。

---

## Retry / Loop / Recovery

```text
Retry
→ 临时执行异常，原样再试

Graph Loop
→ 动作正常执行，但结果不达标

Recovery
→ 原策略不适合继续，换方法
```

---

## Stream / Runner

```python
for chunk in app.stream(
    input_state,
    config=config,
    stream_mode="updates",
):
    ...
```

```text
Graph Loop → 业务修复循环
RetryPolicy → Runtime 重试
Runner Loop → interrupt / resume 外部循环
```

---

## Coding Tools

```text
list_directory → 看结构
list_symbols   → 看类 / 函数
search_code    → 关键词定位
read_file      → 局部读取
replace_text   → 最小修改
write_file     → 新建 / 整文件写入
run_test       → 验证
```

```text
search → 广、浅
read   → 窄、深
```

硬边界放 Tool：

```text
workspace
MAX_READ_LINES
MAX_SEARCH_RESULTS
timeout
exact old_text match
```

---

## Capability Boundary vs Workflow Policy

```text
单次动作始终必须成立
→ Tool / Code

跨多次动作、依赖累计历史
→ State + Graph

需要语义理解 / 动态决策
→ LLM
```

---

## Harness

```text
Completion Guard
→ LLM 不调用 Tool ≠ 任务完成

Tool Call Guard
→ 校验有依赖 Tool 不被错误同批执行

Limit
→ 所有可能循环的 Guard 都要有上限
```

核心：

> 模型越强，Workflow 应该越薄；但安全边界和系统不变量不能因为模型变强而消失。

---

## 意图 vs 事实

```text
LLM → 表达意图
Tool → 产生事实
State → 保存事实
Graph → 根据事实执行规则
```

```text
LLM 想改 a.py
≠ a.py 已修改

LLM 认为测试通过
≠ test_passed=True
```

---

## Context Engineering

```text
少拿
↓
少留
↓
压缩
↓
重要事实放 State
```

```text
Working Summary
→ 当前任务压缩工作现场

Memory
→ 跨任务长期知识

Context Builder
→ Select + Compress + Order
```

推荐：

```text
System Prompt
+ Working Summary
+ Recent Messages
+ 必要 Repo / Memory / State
→ LLM Context
```

> State 保存什么，不等于 LLM 必须看到什么。

---

## Repo Context

```text
Repo Map
→ 仓库有什么

Keyword Search
→ 知道名字时精确找

Semantic Retrieval / RAG
→ 只知道语义时找相关代码

Bounded Read
→ 已定位后读真实代码
```

从粗到细：

```text
目录
↓
文件
↓
Symbol
↓
搜索
↓
局部代码
```

Python AST 可确定性提取 class / function / method，不需要 LLM 猜。

---

## 最终分工

```text
LLM
→ 理解 / 推理 / 动态选择

Tool
→ 执行动作 / 单次硬边界

State
→ 跨步骤结构化数据

Graph / Harness
→ Policy / 完成条件 / 次数 / Guard

Checkpoint
→ 当前任务可恢复现场

Context Builder
→ 当前 LLM 看到什么

Runner / UI
→ Stream + interrupt / resume
```
