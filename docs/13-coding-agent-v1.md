# 13. Coding Agent V1：把所有知识收口成一个完整架构

这一章不是继续加新 API。

目标是把前面的知识组合起来：

> **一个第一版完整 Coding Agent，到底应该怎么分层？**

---

## 1. 需求

V1 需要做到：

```text
用户给出代码修复任务
↓
Agent 自己定位相关代码
↓
读取需要的信息
↓
决定如何修改
↓
写操作必须人工审批
↓
真正修改
↓
运行 pytest
↓
失败可以继续分析 / 修改 / 再测试
↓
最多 3 次正常测试失败
↓
timeout / 环境异常与普通 FAIL 分开
↓
没有真实验证通过，不能宣称 success
↓
最终正式汇报
```

Context 还要满足：

- 不一次读取整个 Repo；
- read_file 有行数上限；
- search 有结果上限；
- 长任务旧历史可以 Summary；
- 最近 Messages 原样保留；
- 修改后的代码需要时重新读取。

---

## 2. 推荐分层

```text
User
↓
Runner / UI
↓
Graph / Harness
↓
LLM
↓
Tool Calling
↓
Tools
↓
Workspace / pytest
```

旁边：

```text
State
Checkpoint
Context Builder
```

---

## 3. LLM 负责什么

交给模型：

```text
读哪个文件
搜什么关键词
Bug 根因是什么
怎么修改
下一步用哪个 Tool
什么时候需要重新观察代码
```

这些需要语义理解和动态判断。

---

## 4. Tools

V1 可以提供：

### Repo / Read

```text
list_files / list_directory
list_symbols
search_code
read_file
```

### Write

```text
replace_text
write_file
```

### Verify

```text
run_test
```

写 Tool 有人工审批。

每个 Tool 自己守住：

- workspace；
- 单次读取限制；
- 搜索结果限制；
- exact-match；
- timeout。

---

## 5. State

不要为了完整塞一堆字段。

一个合理的 V1 候选：

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    working_summary: str

    retry_count: int
    test_passed: bool
    last_error: str
    last_error_type: str

    premature_finish_count: int
    modified_files: list[str]
```

注意：

### 不是所有字段从第一天都必须实现

```text
messages
retry_count
test_passed
last_error
last_error_type
→ 当前核心

working_summary
→ 长任务 Context

premature_finish_count
→ Completion Guard 防死循环

modified_files
→ 当 Graph 有“最多修改 N 个不同文件”的 Policy 时
```

不要默认加入 `current_file`。

---

## 6. Nodes

一种薄 Harness 版本可以只有少量 Node：

```text
chat
tools
sync_state
final
```

外加真正需要独立控制的 Guard：

```text
completion_guard
tool_call_guard
```

Context Builder 如果只是 chat 内部普通处理，可以先做 Python 函数，不急着做 Node。

---

## 7. chat

职责：

```text
构建当前 Context
↓
调用 model_with_tools
↓
返回 AIMessage
```

LLM 不应该自动拿到整个 State。

Context Builder 选择：

```text
System Prompt
Working Summary
Recent Messages
必要 Repo / Memory / State 信息
```

---

## 8. Tool Call Guard

AIMessage 有 Tool Calls 时，先判断是否存在明显依赖冲突：

```text
多个 READ
→ 可执行

WRITE + VERIFY
→ 拒绝同批
→ 给 LLM 反馈重新规划
```

不要把所有智能规划变成固定 Workflow。

只校验必须成立的系统规则。

---

## 9. tools

ToolNode 真正执行 Tool。

高风险写 Tool 内部：

```text
准备具体修改
↓
interrupt
↓
人工批准
↓
真正副作用
```

---

## 10. sync_state

Tool 执行结果进入 messages 后，将 Graph 真正需要的客观事实同步到结构化 State。

例如 run_test：

```text
PASS
→ test_passed=True
→ 清空错误

正常 FAIL
→ test_passed=False
→ retry_count + 1

timeout / environment error
→ last_error_type
→ 不增加普通 retry_count
```

---

## 11. Completion Guard

LLM 不再调用 Tool：

```text
没有 tool_calls
↓
test_passed？
├─ True → final
└─ False → completion_guard
```

Guard：

- 告诉 LLM 当前还没有验证成功；
- 增加 premature_finish_count；
- 未到上限 → chat；
- 到上限 → final，明确报告失败 / 未完成。

---

## 12. 正常失败路由

```text
run_test FAIL
↓
retry_count < MAX_RETRIES
├─ 是 → chat
└─ 否 → final
```

Graph 决定还能不能继续。

LLM 决定怎么修。

---

## 13. 执行异常路由

```text
last_error_type != ""
↓
有真实 Recovery 能力？
├─ 没有 → final
└─ 有 → recovery flow / subgraph
```

不要为了形式感做一个没有新策略的 recovery_node。

---

## 14. Runner

Runner 只负责 Graph 外交互：

```text
app.stream(...)
↓
看到 interrupt
↓
展示给用户
↓
收集批准 / 拒绝
↓
Command(resume=...)
↓
同 thread_id 继续
```

Runner 不做：

- 测试重试策略；
- Tool 依赖判断；
- 成功条件；
- timeout Recovery。

---

## 15. Context V1

```text
从源头：
- search 限结果
- read 限行

历史：
- old history → Working Summary
- recent messages → 原文

事实：
- State

易变信息：
- 需要时重新 read

Repo：
- list / symbols / search / bounded read
```

这已经足够支撑一个实用的第一版。

---

## 16. 推荐 Graph 形状

概念上：

```text
START
  ↓
 chat
  ↓
tool_calls?
 /        \
有         无
↓           ↓
tool_call   completion check
 guard      /            \
↓          可结束        不可结束
tools       ↓               ↓
↓          final        completion_guard
sync_state  ↓               ↓
↓          END             chat
route_after_sync
├─ 普通失败且未超限 → chat
├─ PASS → final
├─ 异常无 recovery → final
└─ 超过限制 → final
```

具体实现可以比图更薄。

---

## 17. 最终职责表

| 层 | 主要职责 |
|---|---|
| LLM | 理解、推理、选择 Tool、提出修改 |
| Tool | 执行动作、产生客观结果、守住单次安全边界 |
| State | 保存跨步骤需要持续存在的结构化数据 |
| Graph / Harness | 确定性 Policy、次数、完成条件、依赖校验 |
| Checkpoint | 保存当前 thread 的执行现场 |
| Context Builder | Select + Compress + Order |
| Runner / UI | 展示 Stream、处理 interrupt/resume、用户交互 |

---

## 18. 接下来进入毕业项目

正式毕业项目不会让你照抄这份图。

会从一个新的需求开始，由你自己决定：

```text
State
Tools
Nodes
Graph Policy
Runner
```

如果卡住，再逐级获得提示。

毕业目标不是“背出这里的 Agent”。

而是：

> **面对一个新的 Agent 需求，能够自己设计出靠谱的执行边界和架构。**
