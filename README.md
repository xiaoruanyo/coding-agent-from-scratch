# 从零构建 Mini Coding Agent

> **一本面向 Agent 零基础程序员的中文实战教材。**  
> 从 LLM、Tool Calling 和 LangGraph 的基本原理出发，最终在本地完成一个拥有 **Python 后端、React 前端、代码检索、文件修改审批、测试执行与任务过程展示** 的小型 Coding Agent 产品。

**这不是“学完框架后顺手交个大作业”，而是以完整产品为目标，反过来设计每一步学习。**

## 先看最终要做成什么

完成必修路线后，用户应能在浏览器里：

1. 打开本地 Mini Coding Agent，看到当前受控工作区。
2. 输入“帮我修复 calculate_total 函数并运行测试”。
3. 实时看到 Agent 搜索、读取、分析和调用工具的过程。
4. 在修改代码之前看到具体 Diff，明确批准或拒绝这一次修改。
5. 查看真实执行结果；测试失败时看到错误和下一次处理，不能凭模型一句话伪造“通过”。
6. 在任务结束时看到修改文件、测试证据与明确的成功／失败／未验证状态。

```text
浏览器：React / TypeScript / Vite
            │
       HTTP + 事件流
            │
Python：FastAPI / Runner / 任务管理
            │
LangGraph：Chat / Approval / Tools / State / Guard
            │
受控工作区：代码检索、最小修改、pytest
```

**本地优先**：从单用户、本机项目开始，不先引入云部署、登录系统或付费基础设施。完整产品并不等于无限功能；边界清晰、从界面到真实执行形成闭环才是重点。

## 按这条路线学习

| 阶段 | 学什么 | 阶段性成果 |
|---|---|---|
| [0. 产品导览](docs/PRODUCT.md) | 先看我们最终要交付什么，怎样验收 | 建立产品全貌 |
| [1. Agent 原理](textbook/README.md) | LLM、Messages、Tool Calling、LangGraph、Reducer、Agent Loop | 可解释最小 Agent 内部流程 |
| [2. 可靠执行与 Harness](docs/INDEX.md#第二阶段可靠-agent-与-harness) | State 事实、Checkpoint、审批、Retry、完成条件、工具边界 | 安全可控的核心执行器 |
| [3. Coding Agent 工程能力](docs/INDEX.md#第三阶段仓库与上下文工程) | 文件检索、Repo Map、Context、精确修改、测试 | 真正处理代码工作区 |
| [4. 前后端产品化](docs/INDEX.md#第四阶段从-agent-core-到完整产品) | FastAPI、React、事件流、Diff、任务状态、集成测试 | 浏览器里操作 Mini Coding Agent |
| [5. 独立验收与扩展](docs/INDEX.md#第五阶段产品验收与进阶扩展) | 端到端测试、故障注入、工程打磨 | 一款可演示、可继续迭代的小产品 |

**详细目录：** [中文课程总导航](docs/INDEX.md) · [最终产品需求与边界](docs/PRODUCT.md) · [系统架构](docs/ARCHITECTURE.md) · [质量与验收标准](docs/DEFINITION-OF-DONE.md) · [写作与代码规范](docs/EDITORIAL.md)

## 这本书怎样讲课？

采用 **系统性技术教材 + 对话式新手教学**：

- 先问一个真实的问题，再解释为什么需要这个机制。
- 先用离线最小示例讲透原理，再放回 Coding Agent 的真实情境。
- 重要 API 给出可以运行的完整脚本，并逐步拆解输入、状态、输出与错误。
- 不把示意性伪代码冒充可运行实现。
- 保留真实学习中容易困惑的提问，例如“为什么条件在 Edge 上”“Reducer 为什么存在”“Tool vs Node”“Checkpoint vs Memory”“Harness 到底是什么”。
- 遇到错误不跳过，也不要求为了凑课时每个小节都做练习。

**读者预备知识：** 能看懂基本 Python 和程序执行流程；不要求 Agent 基础，也不单独开设完整 Python 语法课程。主课程以 Python 为主；React、TypeScript 在产品阶段只讲项目真正需要的部分。

## 课程正文与代码

- [已经编写的详细正文 N00～N18](textbook/README.md)：基础机制、Tool Calling、Graph、Reducer、Harness、审批与多工具执行。
- [随课最小实验](textbook/examples/README.md)：与正文对应的代码、单元测试。
- [产品工程说明](docs/ARCHITECTURE.md)：前端／后端／Agent Core 的职责以及逐步完成路线。

> **完成度说明（重要）**：现阶段是课程重建过程，N00～N18 有详细正文，其余部分按 [课程总导航](docs/INDEX.md) 标示“正在规划／待详细编写”。前端与后端是**必修终点**，不是已经实现并验证的成品。不要把教材的最终愿景当成当前仓库的功能声明。

## 为什么坚持“LLM 负责聪明，程序负责靠谱”？

模型可以决定搜索什么、读哪个文件、怎么修 Bug；但 **工具调用的真实结果、文件权限、用户审批、重试次数、代码验证状态** 要由程序可靠维护。

```text
LLM 提出意图 → Tool 在边界内执行 → 产生可核验的结果
                             ↓
                         sync_state
                             ↓
                   Graph 根据事实做规则判断
```

即使更换更强模型，硬边界也不能被一条 Prompt 替代。

## 项目状态与贡献

本仓库的旧版 `docs/00～13` 是前期学习过程中形成的知识提纲；新版教材正文优先放在 `textbook/`，新的课程体系、产品契约和验收标准放在 `docs/` 的顶层导航中。旧版内容暂留作为历史参考，正式整合时会迁移或归档，**不会要求读者同时沿两套旧目录学习**。

所有提交必须区分：

- 已写完并审校的正文；
- 已经在指定环境运行过的代码；
- 仅说明架构的示意代码；
- 仅计划实现的产品能力。

不上传 API 密钥；不在非受控工作区执行 LLM 生成的任意 Shell。

MIT License。
