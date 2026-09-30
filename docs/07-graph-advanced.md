# 07. Graph 进阶：Command、Subgraph、Parallel、Send

## 1. Command：更新 State + 决定下一步

```python
from langgraph.types import Command
```

Command 常见三种用途：

```text
Command.update
→ 更新 State

Command.goto
→ 指定下一 Node

Command.resume
→ 恢复 interrupt
```

例如：

```python
return Command(
    update={"approved": True},
    goto="execute",
)
```

什么时候适合 Command？

> 当“这个 Node 的执行结果”和“下一步去哪”天然绑定时。

如果只是普通业务节点，Node 返回 State + Conditional Edge 仍然可能更清晰。

---

## 2. Subgraph：Graph 里面的一张小 Graph

当一个局部流程已经有：

- 多个 Node；
- 自己的分支；
- Loop；
- retry / recovery；
- interrupt；

就可以考虑 Subgraph。

```python
subgraph = sub_builder.compile()
parent_builder.add_node("test_flow", subgraph)
```

重点：

> **Subgraph 是流程边界，不等于一定是 State 边界。**

---

## 3. Parent / Child State 怎么共享

优先规则：

```text
同名 + 同语义 + 同类型
→ 可以直接共享

同名 + 不同类型
→ 不共享

同名 + 同类型但语义不同
→ 也不共享

需要转换
→ 显式 Adapter / wrapper
```

不要指望 TypedDict 自动做：

```text
"123" → 123
```

它只是 schema / 类型提示。

---

## 4. Adapter

当父图和子图 State 不一致时：

```text
Parent State
↓
显式映射
↓
Child State
↓
Subgraph
↓
显式映射
↓
Parent State
```

转换应该明确写出来，而不是依赖字段“碰巧同名”。

---

## 5. Subgraph 与 Checkpoint

子图直接作为 Parent Node 使用时，通常可以继承 Parent Graph 的 checkpoint 机制。

```text
Parent compile(checkpointer=...)
+ 相同 thread_id
↓
子图内部 interrupt / resume
```

注意：

> State 是否共享，与 Checkpoint 是否持久化，是两件不同的事。

---

## 6. Parallel / Superstep

Superstep 可以理解成：

> Graph 的一轮执行批次。

同一 Superstep 中可以有多个并行任务。

```text
当前一轮多个任务
↓
全部完成
↓
合并 State 更新
↓
进入下一轮
```

---

## 7. Reducer 为什么在并行时重要

假设两个并行 Node 都返回：

```python
{"results": [...]}
```

如果同一个 channel 没有定义合并规则，就会发生更新冲突。

可以：

```python
from typing import Annotated
import operator

results: Annotated[list[str], operator.add]
```

于是：

```text
分支 A results
+
分支 B results
↓
Reducer
↓
完整 results
```

这也是 Reducer 真正容易理解的使用场景。

---

## 8. Send：动态 Fan-out

```python
from langgraph.types import Send

return [
    Send("analyze_file", {"file": file})
    for file in state["files"]
]
```

注意：

```text
Python for
→ 只是串行生成任务描述

LangGraph Runtime
→ 下一 Superstep 并发执行目标 Node
```

适合：

- 动态文件列表；
- 并行代码分析；
- 并行 review；
- Map-Reduce。

---

## 9. 并行不是越多越好

只有没有依赖的任务才适合并行。

```text
read a.py + read b.py
→ 通常可并行

replace a.py + run_test
→ 有先后依赖
→ 不应同批并行
```

“能并行”与“应该并行”不是一回事。

---

## 10. 本章核心

```text
Command
→ Node 结果与下一跳绑定

Subgraph
→ 封装一段局部流程

Superstep
→ 一轮运行批次

Send
→ 动态创建并行任务

Reducer
→ 多分支写同一 State 时定义合并
```
