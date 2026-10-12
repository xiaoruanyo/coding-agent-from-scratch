# N15｜重试、循环、恢复与完成条件：测试失败以后到底怎么办？

> 本课要解释三个经常混用的词：Retry（原样重试）、Loop（重新分析解决）、Recovery（换策略恢复）。同时回答：为什么模型没有 Tool Calls，并不代表代码修复已经成功？

## 一、四个看起来都像“失败”的场景

**场景一：** 模型服务发生临时连接中断。重新发送同样的请求可能成功，这适合有限的 Runtime Retry。

**场景二：** pytest 真实运行，抛出 `AssertionError: expected 10, got 8`。再次运行同样的未修改代码通常不会改善结果，需要模型重新分析、改变代码，再次测试。这是业务 Loop。

**场景三：** 完整 pytest 一直超时。重复跑相同的命令可能只是不断等待，应尝试定位卡住的测试、缩小范围或者报告环境问题。这是 Recovery。

**场景四：** 用户明确拒绝某次写入。此时不应该把拒绝当成测试失败，也不能未经再次授权执行同一修改；这是审批和任务策略问题。

| 机制 | 是否改变解决方案 | 典型控制层 |
|---|---|---|
| Retry | 不改变；重复相同操作 | Runtime / 有界重试策略 |
| Loop | 改变代码或下一步计划 | LLM + Graph |
| Recovery | 改变失败处理路径 | Graph / Harness / LLM |
| Approval | 决定本次受控操作是否允许 | 用户 + 程序审批层 |

## 二、我们的 V1 约定怎么计数？

用户要求“普通测试失败最多三次”。这句话容易有歧义：是允许第三次失败后继续尝试，还是第三次失败就停止？

我们明确选择后者：

```text
普通 FAIL 第一次 → retry_count = 1 → 可以继续分析
普通 FAIL 第二次 → retry_count = 2 → 可以继续分析
普通 FAIL 第三次 → retry_count = 3 → 停止自动修复，报告失败
```

`TIMEOUT` 与 `TEST_ERROR` 不消耗“普通 FAIL”预算，但必须有独立资源上限和终止路径，不能因此无穷循环。

## 三、为什么需要 sync_state？

工具返回：

```json
{
  "status": "FAIL",
  "exit_code": 1,
  "output": "AssertionError: expected 10, got 8"
}
```

LLM 需要详细报错来分析下一步；Graph 却需要确定的数据：

```python
test_passed = False
retry_count = 2
last_error_type = "TEST_FAIL"
```

所以：

```text
run_test 产生可信结果
      ↓
ToolMessage / 执行记录
      ↓
sync_state：解析结构化事实、更新字段
      ↓
completion_guard：根据字段决定结束还是继续
```

不要用 `if "PASS" in content` 判断测试是否通过，因为 `"Not PASS"` 也包含 `PASS`。状态必须有明确的受控 schema。

## 四、重要陷阱：一个失败结果不能计数两次

Graph 中断恢复、网络重试或运行故障可能导致处理同一个事件的逻辑重复执行。

如果你只写：

```python
retry_count = state["retry_count"] + 1
```

却没有判断本次 `run_test` 的结果是否已经被同步过，就可能把一次 FAIL 记成两次。

可靠方案需要以执行结果或 Tool Call 的唯一 ID 为依据，保证每一次**真正完成的普通失败**只计一次。简单练习阶段可以让 `sync_state` 成为单一写入者；产品阶段要加入事件去重/幂等策略。

## 五、为什么没有 Tool Calls 不能直接 END？

最小 Agent Loop：

```text
chat → 有 tool_calls → tools → chat
        └ 无 → END
```

对加法演示足够。但 Coding Agent 可能返回：

> 我已经修复了所有错误，测试应该也通过了。

如果系统没运行 pytest，它只是一个未经验证的声明。

产品的完成条件应当至少检查：

- 测试是否**真的运行并通过**；
- 上一次测试是不是针对当前代码状态；
- 普通 FAIL 是否达到上限；
- 是否存在等待审批或尚未处理的工具请求；
- 是否有 timeout/异常等无法归入普通 FAIL 的状态；
- 模型是否在没有验证的情况下提前宣布完成。

```text
chat 没有 Tool Calls
       ↓
completion_guard
       ├─ 有当前有效 PASS → 成功报告
       ├─ 普通 FAIL >= 3 → 失败报告
       ├─ 其他错误不可恢复 → 错误报告
       ├─ 未验证且仍可运行 → 继续请求验证
       └─ 再也不能继续 → UNVERIFIED 报告
```

终止和成功是不同概念。`END` 只代表图的执行停止。

## 六、为什么“写入成功”也不等于“任务成功”？

真实执行可能是：

```text
read_file → SUCCESS
replace_text → SUCCESS
run_test → FAIL
```

工具层大部分成功，但业务目标仍没完成。

必须区分：

- **Tool 执行状态**：成功、失败、跳过、拒绝；
- **Test 执行状态**：PASS、FAIL、TIMEOUT、ERROR、NOT_RUN；
- **Task 最终状态**：SUCCEEDED、FAILED、CANCELLED、UNVERIFIED。

前端也必须遵守同一套语义。不能因为聊天消息里出现“完成”，就把任务卡片变成绿色成功。

## 七、测试通过后又修改文件怎么办？

假设：

```text
10:00 pytest PASS
10:01 replace_text 成功
10:02 LLM 回复“完成”
```

10:00 的通过证明的是**写入之前的代码**。若程序仍保留 `test_passed=True` 并据此宣布成功，就是状态设计错误。

因此每次真实成功写入都要使原有的当前版本验证状态失效。进一步可靠性可以记录测试对应的工作区版本哈希，检测外部改动。

## 八、最后的正式报告不要再有写工具能力

`final_report` 只负责输出实际结果：

- 哪些文件**实际**被修改；
- 测试状态来自哪一次真实运行；
- 做过哪些尝试，为什么停止；
- 哪些内容尚未验证。

如果它依然绑定 `replace_text`，就可能在“最终报告阶段”产生额外副作用，破坏完成语义。可以用不带工具的模型生成报告，也可以由程序模板直接组装可靠状态。

## 九、三道设计题

1. 为什么 `pytest` TIMEOUT 不应与普通断言 FAIL 混成同一计数？
2. 用户拒绝一次写入后，Graph 是否一定要结束整个任务？怎样把“拒绝某次修改”和“取消任务”区分开？
3. 模型没有提出新 Tool Calls，但 `test_passed=False`，完成条件应该怎么处理？

**本课核心：失败要分类，重试要有意义，结束要有证据。**
