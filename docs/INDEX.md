# 中文课程总导航

> **主线：从 Agent 的原理出发，最终交付完整本地 Mini Coding Agent。**  
> 本页是知识体系与编写进度的唯一总目录。不要把原先 75 课的对话顺序硬变成 75 个文件；原始课程是素材，新的顺序按知识依赖决定。

## 为什么采用“产品驱动 + 知识依赖”的混合路线？

如果第一页就让读者面对完整 React + FastAPI + LangGraph 代码，新手会被陌生的技术同时淹没。反过来，如果只讲孤立的 LangGraph API，读者很难理解这些机制的实际价值。

我们采用**两个节奏**：

- **知识层**：从小到大，概念必须建立在已解释的基础上。
- **产品层**：每学会一类机制，就知道它最终会落在哪个产品功能里。

例如，理解 ToolMessage 后才能真正理解工具执行过程；理解 `interrupt` 与 Checkpoint 后，才能理解前端的“待审批 → 点击批准 → 继续运行”；理解 State 的事实语义后，才能解释测试状态面板为什么不能直接显示模型的自我评价。

## 第一阶段：理解一个 Agent 怎样工作

这部分已有的详细正文入口：

| 课程 | 主要问题 | 正文 |
|---|---|---|
| N00 | 我们到底要学什么、怎样排错 | [学习方法](../textbook/N00-study-method.md) |
| N01 | Python 解释器、依赖、API 密钥怎样配置 | [环境准备](../textbook/N01-environment.md) |
| N02 | 第一次 `model.invoke` 返回什么 | [调用模型](../textbook/N02-first-model.md) |
| N03 | 为什么“多轮”需要消息历史 | [Messages](../textbook/N03-messages.md) |
| N04 | State、Node、Edge 怎样执行 | [第一张图](../textbook/N04-first-graph.md) |
| N05 | 为什么需要条件边和循环 | [检查—重写循环](../textbook/N05-conditional-loop.md) |
| N06 | Reducer 到底解决什么合并问题 | [Reducer](../textbook/N06-reducer.md) |
| N07 | 模型提出调用请求与真正执行有什么区别 | [Tool Calling](../textbook/N07-tool-calling.md) |
| N08 | ToolNode 怎样组成 Agent Loop | [ToolNode 与 Loop](../textbook/N08-toolnode-loop.md) |

建议在 N05 之后实际运行其离线脚本，在 N08 之后动手观察一次真正的 `AIMessage.tool_calls`、`ToolMessage` 与最终 AIMessage。能解释结果比能复制代码重要。

## 第二阶段：可靠 Agent 与 Harness

| 课程主题 | 要回答的问题 | 状态 |
|---|---|---|
| Harness 是什么 | 为什么 Prompt 不等于运行约束 | [N09 详细正文](../textbook/N09-harness-first.md) |
| Tool 结果同步 State | 测试输出怎样成为可靠的事实 | [N10 详细正文](../textbook/N10-sync-state.md) |
| Human-in-the-loop | 谁负责审批、为什么副作用不能放在 interrupt 前 | [N11 详细正文](../textbook/N11-approval-gate.md) |
| 多 Tool Calls | 整批审批、拒绝、依赖与并行如何处理 | [N12 详细正文](../textbook/N12-batch-tools.md) |
| Checkpoint / thread_id | 中断后如何可靠恢复任务现场 | [N13 详细正文](../textbook/N13-checkpoint-recovery.md) |
| Memory 与 Checkpoint | 长期经验与当前执行现场有什么不同 | 待详细编写 |
| Command / Router / Subgraph | 什么时候需要复杂路由与拆图 | 待详细编写 |
| Retry / Loop / Recovery | 失败重试为什么不是一回事 | [N15 详细正文](../textbook/N15-reliability.md) |
| Completion Guard | 模型说“完成了”为什么不能直接 END | [N15 同章详细解析](../textbook/N15-reliability.md) |
| Stream / Runner | Graph 事件怎样暴露给 UI | 待详细编写 |

这阶段的阶段性成果应该是**能解释一条编码任务的可靠执行链路**，而不仅是知道 `interrupt` 的语法。

## 第三阶段：仓库与上下文工程

| 课程主题 | 产品落点 | 状态 |
|---|---|---|
| Workspace 边界、路径规范化 | 不能读写仓库之外 | [N14 详细正文](../textbook/N14-workspace.md) |
| list_directory / search_code / read_file | 浏览器展示 Agent 的真实代码探索 | [N14 详细正文](../textbook/N14-workspace.md) |
| replace_text / write_file | 可预览、可审批、可核验的文件修改 | [N14 详细正文](../textbook/N14-workspace.md) |
| run_test 的执行安全与结果分类 | 真实测试面板、超时和失败处理 | [N14～N15](../textbook/N15-reliability.md) |
| Context Builder / Working Summary | 长任务不无限增长消息上下文 | [N16 详细正文](../textbook/N16-context-repo.md) |
| Repo Map / Python AST / 搜索阶梯 | 在大型仓库中先导航、再定位、最后读取 | [N16 详细正文](../textbook/N16-context-repo.md) |
| 过期代码与验证失效 | 修改后必须重新观察和验证 | [N16 详细正文](../textbook/N16-context-repo.md) |

不把 “RAG/向量数据库”作为第一版的前置条件。关键词搜索、简单 Repo Map 和局部读取可以先完成可信的 V1。语义检索作为扩展课程，真实需求出现时再加入。

## 第四阶段：从 Agent Core 到完整产品

这一阶段**不是可跳过的扩展**，是课程必修终点。

| 课题 | 最终可见效果 | 状态 |
|---|---|---|
| 产品边界与前后端职责 | 能说清 Browser / FastAPI / Graph 的关系 | [N17 详细正文](../textbook/N17-fullstack-product.md) · [产品契约](PRODUCT.md) |
| 后端任务 API / thread_id | 输入任务、建立任务、查询状态 | 待详细编写 |
| 事件流 SSE / Runner | 前端看到逐步执行进度 | 待详细编写 |
| React 任务输入与 Timeline | 有完整操作界面，而不是终端打印 | 待详细编写 |
| Diff 预览与审批弹窗 | 用户能看清本次修改，再批准或拒绝 | 待详细编写 |
| 测试状态面板 | PASS / FAIL / TIMEOUT / ERROR 真实可见 | 待详细编写 |
| Task 持久化与中断恢复 | 刷新页面或恢复任务不丢失重要现场 | 待详细编写 |
| 前后端集成与故障注入 | 能对真实临时仓库完成端到端修复 | [N18 产品 M0 逐步拆解](../textbook/N18-product-walkthrough.md)（M0 层面已写，完整 V1 仍待实现） |

**可运行的第一条产品化演示链路：** [M0 全栈工程](../product/README.md)。M0 使用确定性驱动器验证真实文件、审批与测试，不应当误认为完整自主 Coding Agent。下一步必须接入 LangGraph + LLM，并完成持久化与安全验收。

推荐技术：Python + FastAPI、LangGraph、React + TypeScript + Vite。选型并不构成架构理论的唯一答案；采用它们是为了让项目有清楚的学习路径。

## 第五阶段：产品验收与进阶扩展

**必修验收**：[验收清单](DEFINITION-OF-DONE.md)——真实测试成功、拒绝审批不写入、失败有解释、UI 展示实际事件、能重新打开任务。

**独立挑战**：给出新的修复任务，学习者独立决定哪些节点、哪些工具、哪些状态，最后完成前后端贯通并解释自己的安全设计。

**独立扩展课程（选修）**：

- 文件树编辑器、行级 Diff、高亮与 Git 操作；
- 语义 RAG／增量索引／多语言 Repo Map；
- 多 Agent、Subgraph 专门工作流；
- Docker/OS 隔离与测试资源治理；
- 任务队列、多用户、远程运行、鉴权；
- Token / 成本统计、可观测性和评测；
- 桌面应用封装、移动端控制；
- 自主经验记忆、Skills、MCP 对接。

扩展功能只有在基础产品经端到端验证之后才考虑引入。

## 章节质量要求

详见 [编辑规范](EDITORIAL.md)。一句话：**每课都要让读者理解“为什么”，看到可核验结果，并知道它最终对应产品的哪个部分。** 无法验证的代码明确标注“示意”；还没写完的课程明确写“待编写”，绝不以课程表冒充正文。
