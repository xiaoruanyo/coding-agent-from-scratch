# 00. 学习路线：我们到底要学什么

## 目标

这套课程不是为了“把 LangGraph API 背下来”，而是为了回答一个更实际的问题：

> **一个 Coding Agent 到底是怎么被设计出来的？**

我们会从最小 LLM 调用开始，逐层加入能力。

```text
LLM
↓
Messages
↓
Tool Calling
↓
Agent Loop
↓
Structured State
↓
Checkpoint / Memory
↓
Human-in-the-loop
↓
Coding Tools
↓
Retry / Recovery
↓
Harness Guard
↓
Context Engineering
↓
Repo Context
↓
完整 Coding Agent
```

## 学习方式

### 1. 先理解职责，再记 API

例如：

```text
Node
→ 做一步工作

Edge
→ 决定下一步

State
→ 在步骤之间传递数据
```

理解之后再看：

```python
StateGraph(...)
add_node(...)
add_edge(...)
```

### 2. 错误不跳过

运行报错时，先搞清楚：

- 错误来自 Python？
- LangGraph？
- Tool schema？
- State 没初始化？
- LLM 返回结构不符合预期？

错误本身也是课程的一部分。

### 3. 不要求死记英文术语

例如：

```text
Progressive Disclosure（渐进式展开）
= 先给粗信息，需要时再展开细节

Retrieval（检索）
= 从大量信息中找当前需要的信息
```

重点记含义，不要求背单词。

## 最终毕业标准

最终不是“会运行教程代码”，而是：

> 给一个新的 Agent 需求，能够自己判断哪些应该交给 LLM、哪些做 Tool、哪些进入 State、哪些由 Graph 保证、哪些属于 Runner / UI。

可以使用 AI 辅助写 Python，但架构判断需要自己完成。
