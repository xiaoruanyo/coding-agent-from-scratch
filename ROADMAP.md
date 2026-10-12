# 课程与产品后续路线（唯一入口见 docs/INDEX.md）

> 该文件保留旧仓库链接兼容性，当前权威进度以 [中文课程总导航](docs/INDEX.md) 为准。

## 已具备的素材与工程

- 详细中文正文 N00～N17：包括 Agent 基础、LangGraph、Tool Calling、HITL、可靠性、Context、产品化设计。
- 随课离线实验与必要的状态同步测试。
- 产品 M0：FastAPI + React + 真实文件 Diff、审批、pytest 与 SSE 的确定性教学原型。它**还不是通用的自主 Coding Agent**。

## 下一步必修里程碑

**M1：LLM 驱动的 LangGraph Agent Core。**

把固定演示驱动器替换为真正的模型决策与受控 Tool Calling，使其能够针对未知任务搜索和读取代码、形成提案。M1 不能因此取消文件写入前审批。

**M2：可靠 Harness 与真实任务状态。**

实现多 Tool Calls 的 ID 完整配对、独立审批节点、sync_state、Completion Guard、普通测试失败预算、超时/错误区分。

**M3：Task Store / Checkpoint 持久化与恢复。**

后端重启之后仍能恢复待审批任务；事件流重连、任务取消、重复审批、用户拒绝应拥有正确状态语义。

**M4：Repo Context 与长任务。**

关键词搜索、Python AST Repo Map、有限读取、Working Summary、版本失效核验与 Token 预算。

**M5：完整产品验收。**

运行 [全链路验收清单](docs/DEFINITION-OF-DONE.md) 后，才能称其为 Mini Coding Agent V1。

## 独立的高级扩展课程

多 Agent、语义 RAG、Docker/OS 隔离、Git 工作流、MCP/Skills、桌面打包、成本/Token 可观测性、多用户远程部署等，是 **V1 完成之后** 可以选择的高级专题。前后端 UI **不是选修扩展**。
