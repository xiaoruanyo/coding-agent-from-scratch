# 系统架构：从一个有状态的 Agent 到浏览器里的 Coding Agent

> 本文描述**目标产品的参考架构**，不是暗示所有模块已经完成。第一次看可以只读前四节；对应概念会在课程中逐步展开。

## 1. 四条链路同时存在

很多入门项目只画一条：

```text
LLM → ToolNode → LLM
```

它描述了模型如何使用工具，却解释不了前端为什么能暂停审批、为何测试失败不是成功、刷新后任务如何恢复。

完整产品至少包含四条交互链路：

1. **控制链路**：用户发起任务 → 后端 Runner → LangGraph 调度。
2. **执行链路**：LLM 提出 Tool Calls → 程序风险检查 → 执行工具 → 返回事实。
3. **状态链路**：真实测试/文件修改 → 同步结构化 State → 完成条件决策。
4. **展示链路**：Graph 事件 → FastAPI 事件接口 → React 时间线、Diff、测试状态。

## 2. 参考架构图

```text
 ┌─────────────────────────────────────────┐
 │ React / TypeScript                      │
 │ 任务输入 | Timeline | Diff | 测试 | 历史 │
 └───────────────────┬─────────────────────┘
                     │ HTTP / SSE
 ┌───────────────────▼─────────────────────┐
 │ FastAPI                                 │
 │ Task API | Approval API | Event API     │
 │ Runner | Session store | Permissions    │
 └───────────────────┬─────────────────────┘
                     │ Graph invoke / resume
 ┌───────────────────▼─────────────────────┐
 │ LangGraph / Agent Core                  │
 │                                         │
 │    chat ─→ approval_gate ─→ tools       │
 │     ▲                          │         │
 │     │                          ▼         │
 │     └───── completion_guard ← sync_state │
 │                       │                 │
 │                  final_report           │
 │                                         │
 │ State | Checkpoint | Context Builder    │
 └───────────────────┬─────────────────────┘
                     │ 受控、可审计的调用
 ┌───────────────────▼─────────────────────┐
 │ 选定的 Workspace                       │
 │ list / search / bounded read           │
 │ replace / new file / restricted pytest │
 └─────────────────────────────────────────┘
```

`approval_gate` 应没有文件写入副作用；`tools` 不能因为模型提出调用就绕过审批；`sync_state` 只以可信执行结果更新程序级事实；`completion_guard` 防止未验证成功。实际路由可能需要从 `chat` 无 Tool Calls 直接进入 Guard，而不是无条件执行审批。

## 3. 三种不同的“状态”

### 模型看到的 Context

由 System Prompt、Working Summary、最近 Messages、适量 Repo 片段组成。上下文是“本次发给模型看的信息”，不等于全部持久化数据。

### Graph State

例如：

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    test_passed: bool
    last_error_type: str
    working_summary: str
```

这是课程讨论过的 V1 初始模型；真正产品可以按完成条件增加字段，但每个字段都要有读写职责，不能把 State 变成日志堆。

### 外部事件／任务存储

UI 需要的时间线、最终报告、审批待办、任务 ID 等，不一定与全部 Graph State 一一相同。应有清晰的数据来源与更新时机，避免三处各写一份互相矛盾的“成功”状态。

## 4. API 边界建议

这些是**建议的 API 语义**，不是已经存在的 HTTP 接口：

| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/workspace` | GET | 当前授权工作区元数据 |
| `/api/tasks` | POST | 新建任务，返回任务 ID |
| `/api/tasks/{id}` | GET | 任务状态、摘要、待审批信息 |
| `/api/tasks/{id}/events` | GET（SSE） | 事件时间线；可断线重连 |
| `/api/tasks/{id}/approval` | POST | 对固定的待审批操作做批准或拒绝 |
| `/api/tasks/{id}/cancel` | POST | 用户明确终止任务 |

### SSE 与后端状态不能混用

SSE 是一种**传送新事件**的机制。它不等于持久化，也不等于真相来源。页面刷新时需要重新查询后端任务状态，必要时根据事件 ID 补齐时间线。

对于可能长时间运行的 Agent，HTTP 请求不应一直阻塞到所有模型调用结束；Runner 可以驱动后台任务，再把事件送到前端。必须保证任务的最大执行时间和取消能力。

## 5. 审批是一个产品行为，不是一个 Python 布尔值

Graph 暂停时，后端应给 UI 返回：

```json
{
  "kind": "file_write",
  "tool_call_id": "call_123",
  "operation": "replace_text",
  "path": "src/calc.py",
  "before": "return a - b",
  "after": "return a + b"
}
```

这只是协议示例，不是框架自带 JSON。用户批准的是该批具体内容，审批后执行层要再次核验内容没有变化，且目录仍在授权范围内。

拒绝意味着这批没有执行，返回模型相应的未执行 ToolMessage；若用户主动取消整个任务，不能把拒绝当作“重新尝试一次”的许可。

## 6. 失败分类与最终状态

不要只有一个 `success: bool` 充当所有阶段的结果。

**工具执行结果**至少区分：

```text
SUCCESS / ERROR / SKIPPED / REJECTED
```

**测试结果**至少区分：

```text
PASS / FAIL / TIMEOUT / ERROR / NOT_RUN
```

**任务状态**可以区分：

```text
RUNNING / WAITING_APPROVAL / SUCCEEDED / FAILED / CANCELLED / UNVERIFIED
```

例如：工具层返回 SUCCESS 表示 `replace_text` 真正修改了文件；它绝不自动使“任务状态”成为 SUCCEEDED。只有对当前修改后的代码获得真实有效测试证据，才有资格标记验证成功。

## 7. 最小安全模型

V1 只允许对可信本地工作区操作，服务默认监听 `127.0.0.1`。HTTP API 仍要检查跨站请求、任务所有权、目录越界、输入大小与具体批准内容；不能把本地端口视为天然无人可攻击。

文件工具至少检查：

- 解析路径属于工作区；
- 不能利用符号链接逃出工作区；
- 操作的文件类型与大小受到限制；
- 精确替换文本必须唯一匹配；
- 写入前重新确认旧内容仍符合预期；
- 记录批准／拒绝、执行结果和工具 ID。

测试运行尤其要注意：固定 `pytest` 命令与超时**不等于 OS 沙箱**。对不可信仓库代码执行测试需要隔离（容器/受限用户/资源边界），作为扩展课程单独讲。

## 8. 前后端技术选型为什么是这一套？

- **FastAPI**：Python 侧能直接复用 LangGraph 状态与工具层；路由和数据模型清晰。
- **React + TypeScript**：适合实现任务时间线、状态订阅、Diff 审批与测试面板；类型能帮助定义清晰 API 契约。
- **Vite**：轻量前端开发服务器，适合本地教学。
- **SSE**：Agent 进度主要是服务端到浏览器的单向事件；比在第一版引入完整 WebSocket 会话协议简单一些。

这些选择都有替代方案，但教材统一采用一种组合，避免新手为了比较十种技术栈而失去主线。

## 9. 哪些地方值得写成独立 Node？

强信号：

- 在两个步骤之间需要条件路由；
- 中间要暂停/审批；
- 需要独立失败处理与重试；
- 权限不同；
- 需要可观测的独立阶段。

“代码一共 200 行”不是充分理由；很多纯 Python 计算放在一个 Node 内就很好。

## 10. 产品化的顺序

```text
先：真实工作区的安全 Tool + 小 Graph
再：State 同步、Checkpoint、人工审批、完成条件
再：FastAPI 任务 API 和事件记录
再：React Timeline、审批 Diff 和测试面板
最后：持久化、故障注入、端到端验收与部署说明
```

产品 UI 不被降级为选修；但复杂 RAG、多 Agent、云多用户等不应阻塞 V1 产品完成。

参考官方资料：

- [LangGraph 中断与恢复](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/)
- [FastAPI Server-Sent Events](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
