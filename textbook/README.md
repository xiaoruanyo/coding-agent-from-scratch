# 从零学习 LangGraph，最终亲手设计 Coding Agent

> **详细教材版 · 正文逐课展开 · 中文优先**  
> 本目录是新版教材。仓库根目录原有的 `docs/` 保留，继续作为旧版知识提纲；`CHEATSHEET.md` 保留作为查询手册。**教材不是速查表，速查表也不应该代替教材。**

## 这套教材适合谁

你可能已经写过程序，却没有系统学过 Agent；能够读懂 Python，但不希望先学习一整套 Python 语言课程；想理解 LangGraph 的 `State`、`Node`、`Edge`、`ToolNode`、`interrupt`、`Checkpoint`；最终希望能够**自己决定一个 Coding Agent 应该怎样设计**，而不是单纯复制一个现成项目。

你不必一开始独立手写所有 Python 代码，可以用 AI 辅助写代码。但你应当能够解释代码为什么这样组织，发现安全边界、状态更新和流程设计中的问题。

## 从头到尾，我们在做同一个项目

```text
第 1 阶段：让模型回答问题
     ↓
第 2 阶段：让模型提出 Tool Calls
     ↓
第 3 阶段：让程序执行工具，并把结果传回模型
     ↓
第 4 阶段：用 LangGraph 管理状态、分支和循环
     ↓
第 5 阶段：加入 Checkpoint、人工审批和失败处理
     ↓
第 6 阶段：提供搜索、有限读取、精确修改、测试工具
     ↓
第 7 阶段：完善 Harness、Context 和 Repo 导航
     ↓
毕业项目：从空目录设计 Coding Agent V1
```

我们要做的 Agent 接到“修复一个 Bug”的任务后，能够寻找相关代码、读取片段、提出修改、经过审批、修改文件、运行测试，并依据**真实结果**决定是否继续；不能因为 LLM 说“已经成功”就宣称测试通过。

## 正文组织方式

这是一个长期维护的教材，而不是把早期 75 课压缩成 13 个 Markdown 的版本。新的课号 `Nxx` 是**教材自己的课号**，不冒充原对话的逐字课号。原 1～75 课的主题可参考根目录 [COURSE_MAP](../COURSE_MAP.md)。

**每一课至少考虑以下教学环节**：要解决的问题、直觉模型、概念精讲、最小代码、逐行解释、预期现象、常见错误、联系 Coding Agent 的设计取舍、理解检查。需要时增加反例和练习；不是为了凑格式，每课都强行给小作业。

### 卷一：基础与最小图

| 课号 | 主题 | 状态 |
|---|---|---|
| [N00](N00-study-method.md) | 学习路线、分层心智模型、如何练习与排错 | 已有正文 |
| [N01](N01-environment.md) | Windows / PyCharm / Python / 环境变量 / API 连接 | 已有正文 |
| [N02](N02-first-model.md) | 第一次调用 Chat Model，理解 invoke 与 AIMessage | 已有正文 |
| [N03](N03-messages.md) | Messages 与多轮对话：到底谁记住了历史 | 已有正文 |
| [N04](N04-first-graph.md) | State、Node、Edge：写出第一张 Graph | 已有正文 |
| [N05](N05-conditional-loop.md) | Conditional Edge、Loop、END：检查—重写循环 | 已有正文 |
| [N06](N06-reducer.md) | Reducer：为什么需要合并更新 | 已有正文 |

### 卷二：Tool Calling 与 Agent 工程入门

| 课号 | 主题 | 状态 |
|---|---|---|
| [N07](N07-tool-calling.md) | @tool、bind_tools、Tool Calls、ToolMessage | 已有正文 |
| [N08](N08-toolnode-loop.md) | ToolNode 与最小 Agent Loop | 已有正文 |
| [N09](N09-harness-first.md) | Harness 的实际含义、薄 Workflow 和安全边界 | 已有正文 |
| [N10](N10-sync-state.md) | 工具事实如何同步成 State；普通失败与 timeout | 已有正文 |
| [N11](N11-approval-gate.md) | interrupt、独立审批节点、恢复和拒绝 | 已有正文 |
| [N12](N12-batch-tools.md) | 批量审批、多 Tool 配对、依赖与并行 | 已有正文 |

### 卷三：可靠执行、真实仓库与产品衔接

| 课号 | 主题 | 状态 |
|---|---|---|
| [N13](N13-checkpoint-recovery.md) | Checkpoint、thread_id、interrupt 恢复与重放副作用 | 已有正文 |
| [N14](N14-workspace.md) | 受控工作区、局部读取、精确修改与 pytest 边界 | 已有正文 |
| [N15](N15-reliability.md) | Retry、Loop、Recovery、sync_state 与完成条件 | 已有正文 |
| [N16](N16-context-repo.md) | Working Summary、Context Builder、Repo Map 与过期上下文 | 已有正文 |
| [N17](N17-fullstack-product.md) | FastAPI、React、SSE、Diff 审批与产品路线 | 已有正文 |

[随课代码与离线测试](examples/README.md)

[产品 M0：本地运行的 FastAPI + React + 真实 Diff 与 pytest 演示工程](../product/README.md)

### 后续卷：待编写详细正文

这些是 **规划中的主题**，不是已经完成的教材：

- **状态与持久化深化：** 长期 Memory / Store、持久化 Checkpointer、恢复幂等与多会话授权。
- **Coding Agent 工具链深化：** 更完整的 AST 搜索、内容版本核验、安全执行与工具错误矩阵。
- **Graph 进阶：** Command、Subgraph、Parallel/Superstep/Send、RetryPolicy、Stream、Runner、Recovery。
- **Harness 进阶：** Completion Guard、Tool Call Guard、跨步骤 Policy、事实一致性、状态最小化。
- **Context Engineering 深化：** Token 预算、摘要触发策略、代码依赖图和按需的语义检索。
- **产品必修：** 把 M0 演示驱动器替换为 LangGraph + LLM，打通完整自主任务、审批恢复、真实测试与 React UI，再进行端到端验收。

未来的详细正文将从 N18 起继续完善。已有内容与待写的内容严格分开，不能把课程规划标成“已完成”。

> **编写状态是真实状态，不是学习进度。** 没有详细正文的课绝不写成“已完成”。原版课程里已经讲到的概念，不代表这个新版教材的正文已经写好了。

## 学习要求

1. 先看解释，再运行代码，最后观察输出；不要看见 `invoke()` 就认为已经理解 `State` 更新。
2. 出现报错先定位错误在哪一层：Python、API 请求、Tool schema、消息协议、Graph 路由、State 字段、外部环境。
3. 对代码中的安全约束，不以一句“模型会注意的”作为保证。
4. 不是每课都要做习题；关键章节要能**解释为什么这么设计**。
5. 速查时使用 [CHEATSHEET](../CHEATSHEET.md)；学习时看完整教材正文。

## 参考项目与版本说明

本教材的历史实践环境包含 Windows、PyCharm、Python 3.13、`langgraph==1.2.11` 和通过兼容接口调用的 DeepSeek。第三方模型名可能变化；教程代码会尽量从环境变量读取模型名，避免把某个时间点的名称写死为永久有效。

**教材代码并不是对所有 LangGraph / LangChain 版本的兼容保证。** 每课标注必要依赖；涉及 API 版本差异时优先以实际安装版本检查。未实测运行的示意代码会明确标注。

## 内容来源与编辑原则

这套教材以此前的学习对话、仓库既有 13 章概要及相关代码练习为主线，保留实际出现的困惑与错误（例如 `compile` 与 `compiled`、函数引用与函数调用、缺失 `check_count` 初值、多 Tool 的调用配对）。为了构建连续的教材，需要重新组织、补充解释和重写例子；**不把重新编写的段落假称为历史对话原文**。

我们始终保持一句主线：

> **LLM 负责聪明，程序负责靠谱。**
