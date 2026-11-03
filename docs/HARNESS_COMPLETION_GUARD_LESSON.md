# Harness 工程课：Completion Guard 与过期验证证据

> 状态：2026-11-03 教学笔记。**学习者尚未完成手写与真实环境验证**。当前工作区文件和本地测试报告以用户电脑实际状态为准，不以 GitHub main 旧文件代替。

## 为什么需要 Completion Guard？

任务：“修复 calculator.py 并通过 pytest”。

1. Agent 产出代码版本 A。
2. pytest 对版本 A 执行，退出码为 0。
3. Agent 又修改一次文件，得到版本 B。
4. LLM 声称“所有测试通过，任务完成”。

版本 A 的通过证据不能证明版本 B 通过。这是 **Stale Test Evidence（测试证据过期）**，不是单纯的 Prompt 不够好。

**工程原则**：LLM 的完成声明是意图/建议；工具的退出码和被测试的代码快照才是证据。没有有效证据就不允许把任务标记为 COMPLETED。

## Completion Guard 需要的最小事实

| 字段 | 数据来源 | 语义 |
| --- | --- | --- |
| current_revision | 程序按实际文件内容计算版本指纹 | 当前工作区代码版本 |
| tested_revision | 测试运行时记录的版本指纹 | 上一次测试验证的版本 |
| test_exit_code | 实际测试工具的进程退出码 | 0 为测试执行成功的必要条件（不等于满足全部验收标准） |
| pending_approval | 审批状态机 | 是否仍有待批准的修改 |
| pending_tools | 执行器任务队列 | 是否有尚未完成的工具操作 |
| goal_verified | 验收流程的明确证据 | 是否已经满足目标验收条件，不应由模型直接声明为真 |

建议 Guard 以结构化结果返回 `(allowed, reason)`，区分：`PENDING_APPROVAL`、`PENDING_TOOLS`、`TEST_NOT_PASSED`、`STALE_TEST_EVIDENCE`、`GOAL_NOT_VERIFIED`、`COMPLETED`。

**易错点**：
- `test_passed=True` 不等于当前文件状态已经验证。
- 只看 Git commit hash 可能遗漏未提交修改；只看单文件 hash 不能覆盖依赖、测试文件与运行环境。
- 检查版本时机很关键：测试开始前/结束后应核对快照；如果过程中相关文件发生变化，不能把测试结果绑定为有效当前证据。
- 如果是文档生成等不需要 pytest 的任务，应按任务类型选择对应验证策略，不能所有任务强迫 `pytest`。
- 对于正在运行的异步工具和待审批操作，不应提前将任务标为 COMPLETED。

## 推荐的学习方式：真实模型 + 自己写核心 Guard

本课不再模拟 LLM。继续使用本地 Mini Coding Agent 的“AI 查看代码”让 DeepSeek 读取 calculator.py，观察真实请求、授权和 Tool 结果。

然后学习者**亲手实现 Completion Guard 的纯函数**，通过确定性用例测试 A→B 的证据过期。纯函数的单元测试不需要重复收费调用 LLM，并不意味着模拟 LLM。

本地文件快照的最小示例：

```python
import hashlib
from pathlib import Path

def file_revision(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()
```

这只能证明**一个文件**的内容是否变化，是第一版教学实验；成熟 Harness 应考虑多文件、工作区快照、测试执行环境、外部并发修改与验证命令。

## 手写任务

定义：
```python
from dataclasses import dataclass

@dataclass
class Evidence:
    current_revision: str
    tested_revision: str | None
    test_exit_code: int | None
    pending_approval: bool
    pending_tools: bool
    goal_verified: bool
```

实现 `completion_guard(state: Evidence) -> tuple[bool, str]`：

1. 如果存在待审批 / 未完成工具，拒绝完成；
2. 如果未有成功测试的记录，拒绝完成；
3. 如果测试版本与当前版本不同，返回 `STALE_TEST_EVIDENCE`；
4. 如果未通过目标验收，拒绝完成；
5. 否则允许结束。

先用最少 4 个确定性输入验证（A/A、B/A、测试失败、待审批），再考虑接到 LangGraph 中的最终完成路径。

## 为什么不能只放 Prompt？

无效约束：“修完之后记得重新测试，否则不要说完成。”

Prompt 是行为引导而不是强制边界。System Prompt 仍然值得优化，但最终完成决定必须由代码核对结构化状态与工具证据。

建议单次开发任务契约：

```text
目标：对 Mini Coding Agent 的完成条件增加可靠校验。
现状：已有 LLM read_file、工具执行记录、M0 Diff / pytest 演示与横向工作台。
本轮重点：我亲手实现 completion_guard 纯函数；
Trae 只负责审查代码、补充回归测试与后续 UI/Runner 集成。
约束：测试结果必须绑定被验证的代码版本；不能依赖模型声称“测试通过”。
不改写已有未提交文件；不对生产环境运行工具；不自动发起多次收费模型调用。
验收：A 版本测试成功→允许；B 修改后未重测→拒绝；
测试失败/审批未完成/工具未结束→拒绝；每种场景记录明确原因。
交付：真实运行的测试命令与结果、修改文件、可能缺失的验证覆盖范围。
```

## Harness 演进问题

- 修改后如何失效既有测试证据（invalidate-on-write）？
- Test Runner 如何保证验证对象是执行前后同一个代码快照？
- 哪些文件属于验证范围？仅 calculator.py 的 hash 为什么不够？
- 多任务同时修改仓库时，如何防止并发导致结果过期？
- 测试通过 ≠ 用户验收条件全部满足；哪些条件必须显式核验？

下一步：完成纯 Guard 后，再由学习者把 Guard 设计成 LangGraph 的完成关卡；外围 Runner 和 UI 由 Trae 集成。
