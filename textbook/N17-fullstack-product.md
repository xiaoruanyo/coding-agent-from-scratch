# N17｜为什么最终必须有前后端：从 LangGraph 到真正可操作的 Mini Coding Agent

> 本课进入产品阶段。我们不是顺手给终端脚本加一个聊天框，而是把任务、工具执行、审批、测试与报告变成能从浏览器操作、追踪和核验的流程。

## 1. 第一次看产品架构，先不要同时学习十套技术

```text
React 页面
  ↓ HTTP 发任务 / 审批
FastAPI Runner
  ↓ invoke / stream / resume
LangGraph Agent Core
  ↓ 受控 Tool
本地 Workspace / pytest
  ↑ 真实结果
Agent State / Event Store
  ↑ SSE / 任务查询
React 时间线 / Diff / 测试面板
```

这不是单纯的部署图，而是不同职责边界：

- React：展示状态、收集用户输入与审批，不直接拥有工作区写入权限。
- FastAPI：任务 ID、请求校验、事件流和 Runner，绑定用户操作与具体 Graph 线程。
- LangGraph：模型、工具、状态、条件路由、中断与完成条件。
- Workspace/Tools：在授权边界内产生真实环境事实。
- Checkpointer/Task Store：保存运行现场和 UI 历史。

## 2. 一个“开始任务”请求应该做什么？

前端用户输入：

> 修复计算函数并运行测试。

最简单的 API：

```http
POST /api/tasks
Content-Type: application/json

{"instruction":"修复计算函数并运行测试"}
```

后端返回：

```json
{
  "task_id": "task-001",
  "status": "RUNNING"
}
```

这里的字段是我们自己设计的产品协议，并不是 LangGraph 自带响应格式。

**不要让一个 HTTP 请求无限等待整个 Agent 任务完成**。更完善的 Runner 应在后台驱动 Agent，再提供任务状态和事件接口。对于课程的 M0 演示，可以先以同步方式验证审批与真实测试，然后在后续课程中升级为后台任务驱动。

## 3. 为什么 UI 需要事件流？

用户希望看到 Agent 在做什么，而不仅是最后一句“完成”。

可能的事件：

```text
TASK_CREATED
TOOL_REQUESTED search_code
TOOL_RESULT search_code → 命中 3 处
TOOL_REQUESTED read_file
TOOL_RESULT read_file → 阅读代码片段
APPROVAL_REQUESTED → Diff
APPROVAL_ACCEPTED
TOOL_RESULT replace_text → 修改成功
TEST_STARTED
TEST_RESULT → FAIL
TASK_FINISHED → FAILED
```

这些事件的含义必须来自实际执行过程。例如 `TOOL_REQUESTED` 表示“模型想执行”，`TOOL_RESULT` 才代表“工具确实执行并返回”。

SSE 是从后端到浏览器的单向事件通道，适合这个场景。浏览器用 `EventSource` 订阅后端事件，普通按钮操作继续通过 HTTP POST 完成。

## 4. SSE 不是真相数据库

一个经常出现的错误做法：

```text
React 收到 “测试开始” 事件
→ 把状态改为 PASS
```

这是把“发生了事件”和“事件证明什么”混淆了。

正确做法：

- 后端权威 Task Store 保留当前任务状态和真实测试结果；
- SSE 负责高效通知页面发生了变化；
- 页面刷新时，重新 GET 当前状态，而不是从本地缓存推断一切；
- 断线重连时有事件游标/ID 或重新取快照机制。

产品里的状态枚举至少要区分任务的 RUNNING、WAITING_APPROVAL、SUCCEEDED、FAILED、CANCELLED、UNVERIFIED，以及测试的 NOT_RUN、PASS、FAIL、TIMEOUT、ERROR。

## 5. Diff 审批不只是两个按钮

审批 UI 至少展示：

- 项目/文件路径；
- 将被替换的旧文本；
- 拟写入的新文本；
- 操作名、对应工具调用；
- 当前文件版本或提案摘要。

后端必须校验用户提交的决定确实属于**当前待审批请求**。

例如：

```json
{
  "approved": true,
  "proposal_id": "proposal-abc123"
}
```

这里 `proposal_id` 是产品可以设计的稳定提案 ID。不能用前端按钮文字作为唯一凭证，也不能让模型在审批后悄悄改变工具参数。

如果用户明确取消整个任务，与单纯拒绝某一次修改不同；后端也必须阻止正在排队的写入继续执行。

## 6. “最小产品”为什么从确定性演示驱动器开始？

假设第一次启动全栈项目，同时依赖：

- 前端组件与状态同步；
- HTTP、CORS、事件流；
- LangGraph 依赖；
- API Key；
- Tool Calling；
- 文件审批；
- pytest 执行；
- Checkpoint 和恢复。

任何一个环节出错都可能使整个产品看似不可用。对新手非常不友好。

因此课程先提供 [产品里程碑 M0](../product/README.md)：固定样例 Bug，但真实走完

```text
浏览器发任务
→ FastAPI 生成真实 Diff
→ 用户在浏览器审批
→ 后端确实修改了样例 Python 文件
→ 真实 pytest
→ 浏览器显示验证结果
```

**M0 不是完整 Agent**，它只是一次可重复、可独立排错的产品通道验证。后续通过 M1/M2 接入真实 LLM 和 LangGraph，再实现动态任务处理。

## 7. 产品原型与真正 Agent 的分界

| 里程碑 | 能力 | 可以怎样描述 |
|---|---|---|
| M0 | 固定教学 Bug 的完整 UI/后端/审批/测试链路 | “可运行的产品化演示原型” |
| M1 | LangGraph/LLM 动态选择工具、维护状态 | “具备自主规划的初版 Agent” |
| M2 | Checkpoint/Guard/多调用安全/可核验结果 | “可靠性增强的 Agent Core” |
| M3 | 持久化、事件恢复、取消与状态一致性 | “可恢复的本地产品” |
| V1 | 端到端产品验收全部满足 | “完整 Mini Coding Agent V1” |

不能因为 UI 看起来完整，就提前宣称全部工作已经完成。

## 8. 真实错误排查顺序

**页面请求 404**：先检查 Vite 代理和 FastAPI 路由，别去改 LangGraph。

**创建任务成功，但页面无事件**：检查 SSE endpoint、EventSource 订阅、任务 ID、浏览器网络面板。

**UI 显示 WAITING_APPROVAL，但按钮无效**：检查 proposal ID、后端任务状态和审批恢复路由。

**工具写入成功，UI 仍显示 NOT_RUN**：检查是否真正触发 run_test，以及测试结果是否被同步到后端 Task Store。

**模型自称成功，测试面板显示失败**：UI 应显示失败；修复的是 Agent 的完成条件和状态同步，而不是让 UI 相信模型。

**刷新之后任务消失**：如果当前还是内存 Task Store，这正是 M0 已知限制；要达到产品 V1，需要持久化与恢复能力。

## 9. 最小前端应该有哪几块？

- 工作区与最近任务；
- 任务输入框；
- 执行 Timeline（真实工具事件）；
- Diff 审批面板；
- 测试输出与状态；
- 最终报告。

这些 UI 都有对应的后端数据源，避免堆砌看似高级但与真实 Agent 执行无关的装饰。

## 10. 本课理解检查

1. 为什么 UI 不应该直接根据 LLM 回答设置 SUCCESS？
2. 为什么 SSE 与任务状态存储不能互相替代？
3. 为什么审批必须绑定具体提案？
4. 为什么先做 M0 并不是降低最终产品的目标？
5. 要宣称“刷新/重启后任务能恢复”，需要验证哪些存储和恢复链路？

最终要理解：**完整产品并不只是在 Graph 外面套一个前端，它要求任务、执行、授权、状态和展示遵循同一组事实。**
