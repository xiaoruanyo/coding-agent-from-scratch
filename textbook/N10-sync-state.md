# N10｜sync_state：ToolMessage 怎么变成 Graph 能判断的真实状态？

> 本课从一个毕业项目设计选择开始：Tool 执行 `pytest` 后，是它顺便更新所有 State 字段，还是由独立的 `sync_state` 根据结果转换？我们在 V1 选择后者，以便把“执行事实”和“跨步骤策略状态”分开。

## 1. 为什么仅有 ToolMessage 还不够？

模型请求运行测试，`run_test` 返回：

```json
{
  "status": "FAIL",
  "exit_code": 1,
  "output": "AssertionError: expected 10, got 8"
}
```

对于 LLM 来说，这段测试输出已经足以开始分析原因。

但对于 Graph 来说，我们还需要可靠的数据：

```python
test_passed = False
last_error_type = "TEST_FAIL"
retry_count = 1
```

特别是用户要求：

> 普通测试失败最多允许三次，超时要单独处理。

如果只是把测试日志放进 Messages，然后让模型判断“我们已经失败几次”，就把程序级规则交给了可能犯错的文本推理。

## 2. 两种设计方案

### A：Tool 直接修改 State

```text
run_test
  ├─ 执行 pytest
  ├─ 写 test_passed
  ├─ 更新 retry_count
  └─ 决定失败类型
```

某些简单系统可以这么做，但它让一次外部动作与整个 Graph 的任务规则紧密耦合。

### B：Tool 只返回事实，再做同步

```text
run_test（执行事实）
      ↓
ToolMessage / 结构化执行记录
      ↓
sync_state（转换到 Graph State）
      ↓
test_passed / retry_count / last_error_type
```

我们选择 B，不是因为 A 永远错误，而是因为 V1 有明确的**测试分类、次数上限和完成条件**，值得把转换单独拆开，便于测试和审计。

## 3. 核心风险：Tool 的自然语言并不是程序契约

最脆弱的做法：

```python
if "PASS" in tool_message.content:
    return {"test_passed": True}
```

看似简单，却可能出错：

```text
"Previously PASS, current run FAIL"
"Expected output: PASS"
"Tests did not PASS"
```

这些字符串都可能包含 `PASS`，但真实状态不是成功。

所以，如果程序要可靠判断，最好先让工具返回结构化结果，而不是靠关键词猜。

## 4. 设计一个结构化的测试结果

例如先定义 Python 类型：

```python
from typing import Literal, TypedDict

class TestResult(TypedDict):
    status: Literal["PASS", "FAIL", "TIMEOUT", "ERROR"]
    exit_code: int | None
    output: str
```

语义：

- `PASS`：测试命令运行完成且按约定报告成功。
- `FAIL`：测试真正运行了，但断言或测试检查没有通过。
- `TIMEOUT`：在规定时间内未完成。
- `ERROR`：测试命令无法正常运行，或发生其他执行异常。

这四类状态是我们在课程里约定的**应用层 schema**，不是 pytest 自带的统一 JSON 返回格式。需要由 `run_test` 的包装代码根据进程运行结果转换。

### 如何判定 PASS？

例如 subprocess 在受限工作目录运行固定命令：

```python
[sys.executable, "-m", "pytest"]
```

通常可以根据进程是否正常结束以及退出码判断结果，同时保留有意义的输出。

但应认识到：pytest 的各种退出码有细分语义，诸如找不到测试、错误的命令行参数或内部错误，不应该为了图省事都称为普通断言失败。正式实现应更精确地分类。

## 5. sync_state 做什么？

先给**不依赖 LangGraph 的纯函数**，只演示状态转换规则：

```python
from typing import TypedDict

class TestResult(TypedDict):
    status: str
    exit_code: int | None
    output: str

def sync_test_result(
    *,
    result: TestResult,
    previous_retry_count: int,
) -> dict:
    status = result["status"]

    if status == "PASS":
        return {
            "test_passed": True,
            "last_error_type": "",
            "retry_count": previous_retry_count,
        }

    if status == "FAIL":
        return {
            "test_passed": False,
            "last_error_type": "TEST_FAIL",
            "retry_count": previous_retry_count + 1,
        }

    if status == "TIMEOUT":
        return {
            "test_passed": False,
            "last_error_type": "TEST_TIMEOUT",
            "retry_count": previous_retry_count,
        }

    return {
        "test_passed": False,
        "last_error_type": "TEST_ERROR",
        "retry_count": previous_retry_count,
    }
```

这是一套明确的 V1 业务策略：

**普通测试 FAIL 才增加“普通失败”计数；timeout 和其他 ERROR 不混入这个计数。**

该函数不做 LLM 推理，不读取磁盘，不执行新工具，只根据已有真实结果转换字段。

## 6. 把转换放在 Graph 的什么位置？

```text
chat（请求 run_test）
       ↓
tools（pytest 真实运行）
       ↓
sync_state（读取对应 run_test 结果）
       ↓
completion_guard（根据字段决定下一步）
```

`sync_state` 必须知道读取的是哪一条 `run_test` 的真实结果。不能随便取历史最后一条 Message 就假设它是测试结果，因为一个 AIMessage 可能同时请求多个 Tools。

实际实现时，可以采用：

- 有明确定义的结构化 Tool 结果；
- 保留 `tool_call_id` 与工具名关联；
- 对应 ToolMessage 的可解析数据或受控执行记录；
- 确保同一次测试结果不会因为恢复/重试重复累计。

后面这条“不可重复计数”很重要，特别是 `interrupt` 恢复、节点重复执行或程序重试时。

## 7. 一个更隐蔽的问题：测试通过不代表代码一直有效

假设时间线：

```text
10:00 运行测试 PASS
10:01 再次修改 main.py
10:02 LLM 说“完成”
```

如果 State 一直保留 `test_passed=True`，是否可以宣称成功？

**不能简单这样判断。**

因为 PASS 验证的是**先前版本**的代码。之后又改了文件，原来的成功不能自动证明当前工作区仍然通过测试。

V1 至少应有一条不变量：

> 任何成功的写入都会使已有的“当前版本已验证”结论失效，直到对修改后的工作区重新运行并通过测试。

最小实现可在同步写入成功时设置 `test_passed=False`。更严格的工程实现可以记录被验证的工作区版本或内容摘要，防止工作区在验证后被外部进程修改导致状态过期。

这个问题说明：**State 的值要有清晰的时效语义。**

## 8. retry_count = 3 到底意味着什么？

如果用户说“普通失败最多 3 次”，我们要先定义计数口径：

- 是允许第 3 次失败后再修一次？
- 还是累计到第 3 次普通失败就停止？

我们的 V1 约定：

> **累计第三次普通测试 FAIL 后停止自动修复，进入失败汇报。**

例如：

```text
第一次 FAIL → retry_count = 1 → 可以修复再测
第二次 FAIL → retry_count = 2 → 可以修复再测
第三次 FAIL → retry_count = 3 → 不再自动继续，报告失败
```

这样 `completion_guard` 就可以用明确的阈值，而不是让模型猜“最多三次”包含哪些边界。

## 9. 为什么 `sync_state` 要独立测试？

因为它是系统正确性的关键连接点。

可以给纯函数做单元测试：

```python
def test_normal_fail_increments_counter():
    out = sync_test_result(
        result={"status": "FAIL", "exit_code": 1, "output": "assert failed"},
        previous_retry_count=2,
    )
    assert out["retry_count"] == 3
    assert out["test_passed"] is False

def test_timeout_does_not_consume_normal_fail_budget():
    out = sync_test_result(
        result={"status": "TIMEOUT", "exit_code": None, "output": ""},
        previous_retry_count=2,
    )
    assert out["retry_count"] == 2
    assert out["last_error_type"] == "TEST_TIMEOUT"
```

这类规则的行为应该由单元测试证明，而不是通过几十轮真实 LLM 调用碰运气。

## 10. 完成条件必须使用事实

在 V1 中，`completion_guard` 不应该根据 `AIMessage.content` 里有没有“修好了”来决定成功。

它应该检查：

- 是否有真实通过的测试；
- 通过的测试是否仍对应当前代码状态；
- 普通失败次数是否到上限；
- 最近错误是否超时或执行异常；
- 本轮是否仍有必须处理的工具执行结果。

所以：

```text
LLM：“我觉得修好了”
≠
test_passed=True
```

只有通过程序可验证的结果，Graph 才允许宣称 SUCCESS。

## 11. 本课常见误区

**误区：ToolMessage 是 dict，所以 Graph 自定义 State 自动变化。**

不自动。Tool 输出通常首先属于工具消息；把它同步到自定义 State 需要明确程序逻辑，除非你另行设计了直接更新 State 的工具模式。

**误区：每种错误都增加同一个 retry_count。**

会混淆业务失败和执行失败，不符合我们的 V1 需求。

**误区：测试曾 PASS，之后随便改文件仍算 PASS。**

忽略了测试结果与工作区版本的一致性。

**误区：把整个 pytest traceback 放进 last_error 字段。**

不一定有必要。详细日志可保留在消息/运行记录中；Graph 只需要可靠分类时，`last_error_type` 通常更合适。

## 12. 理解检查

1. 为什么 `sync_state` 不能只检查“PASS”字符串？
2. 为什么 timeout 不应该默认消耗普通 FAIL 预算？
3. `ToolMessage` 与 `test_passed` 字段分别服务于谁？
4. 修改代码成功后，之前的 PASS 为什么可能失效？
5. 第三次普通 FAIL 时我们的 V1 应该走向哪里？

下一课：[N11｜人工审批](N11-approval-gate.md)。
