# 从零开始构建 Coding Agent

> 用一个持续演进的 Coding Agent，系统学习 LangChain、LangGraph、Tool Calling、State、Checkpoint、Memory、Human-in-the-loop、Agent Harness、Context Engineering 与代码检索。

这不是一份只讲 API 的 LangGraph 笔记。

这套教程的主线始终只有一个：

> **从最小的 LLM 调用开始，一步一步做出一个真正可运行、可控制、可恢复、可扩展的 Coding Agent。**

课程优先使用中文。专业英文术语第一次出现时会同时给出中文解释，目标是理解概念，而不是背英文。

---

## 最终要做出的 Agent

```text
用户提出代码任务
        ↓
Agent 理解任务
        ↓
浏览 / 搜索 / 读取 Repo
        ↓
分析问题并决定修改方案
        ↓
高风险写操作人工审批
        ↓
真正修改代码
        ↓
运行测试
        ↓
  ┌─────┴─────┐
  ↓           ↓
通过        失败 / 异常
  ↓           ↓
最终报告   修复 / Retry / Recovery
              ↓
             再验证
```

最终核心能力包括：

- LLM 与 Messages
- Tool Calling / ToolNode
- State / Reducer
- Conditional Edge / Loop
- Checkpoint / Memory
- Human-in-the-loop
- 文件搜索、局部读取与最小修改
- Retry / Loop / Recovery
- Stream / Runner
- Completion Guard / Tool Call Guard
- Working Summary / Context Builder
- Repo Map / AST / 分层代码检索
- 一个完整的 Coding Agent Core

---

## 核心设计原则

贯穿整套课程的几句话：

> **LLM 负责聪明，程序负责靠谱。**

> **能用确定代码判断的，就不要交给 LLM 猜。**

> **模型越强，Workflow 应该越薄；但安全边界和系统不变量不能因为模型变强而消失。**

> **LLM 负责表达意图，Tool 负责产生事实，State 负责保存事实，Graph 根据事实执行规则。**

> **Context 不是越多越好，而是越相关越好。**

---

## 课程目录

| 章节 | 内容 |
|---|---|
| [00. 学习路线](docs/00-course-guide.md) | 学习方式、环境、课程主线 |
| [01. LangChain 最小基础](docs/01-langchain-basics.md) | LLM、Messages、多轮对话 |
| [02. LangGraph 基础](docs/02-langgraph-basics.md) | State、Node、Edge、Loop、Reducer |
| [03. Tool Calling 与 Agent Loop](docs/03-tool-calling.md) | @tool、bind_tools、ToolNode、多 Tool |
| [04. State、Checkpoint 与 Memory](docs/04-state-checkpoint-memory.md) | 结构化状态、持久化、长期记忆 |
| [05. Human-in-the-loop](docs/05-human-in-the-loop.md) | interrupt、Command、人工审批 |
| [06. Coding Agent 工具链](docs/06-coding-tools.md) | sandbox、search、bounded read、replace_text |
| [07. Graph 进阶](docs/07-graph-advanced.md) | Command、Subgraph、Parallel、Send |
| [08. 可靠执行](docs/08-reliability-runtime.md) | RetryPolicy、Stream、Runner、Recovery |
| [09. Agent Harness](docs/09-agent-harness.md) | Completion Guard、Tool Call Guard、薄 Workflow |
| [10. State 设计与事实模型](docs/10-state-and-facts.md) | 意图 vs 事实、State 最小化 |
| [11. Context Engineering](docs/11-context-engineering.md) | Summary、Memory、Context Builder、过期上下文 |
| [12. Repo Context](docs/12-repo-context.md) | Repo Map、AST、RAG、渐进式展开 |
| [13. Coding Agent V1 架构](docs/13-coding-agent-v1.md) | 把全部知识收口成完整 Agent |
| [课程课号映射](COURSE_MAP.md) | 原 1～75 课对应到新的章节 |
| [速查笔记](CHEATSHEET.md) | API、概念、架构原则快速查询 |
| [后续路线](ROADMAP.md) | 毕业项目、工程化、FastAPI / React 扩展 |

---

## 推荐学习方式

每章建议按这个顺序：

```text
先理解为什么
↓
看最小代码
↓
自己运行
↓
观察真实输出
↓
出现错误先解决
↓
再进入下一节
```

不要求为了学习而手敲所有代码。可以使用 AI / IDE 辅助编码，但需要能够：

- 看懂 Agent 的关键结构；
- 判断 LLM / Tool / State / Graph / Runner 的职责；
- 发现架构设计不合理的地方；
- 给 AI 明确的修改要求；
- 最终从空目录设计出自己的 Coding Agent。

---

## 实践环境

本教程形成过程中的主要实践环境：

```text
Python 3.13
LangGraph 1.2.11
langchain_openai.ChatOpenAI
DeepSeek API
pytest
```

示例以 Python 为主，但课程重点是 Agent 架构，不是 Python 语法课程。

---

## License

MIT License
