# N11｜Human-in-the-loop：为什么选择独立的 approval_gate？

> 本课来自毕业项目里的一次具体架构选择：修改文件必须审批，我们选择把审批做成独立的 `approval_gate` Node，因为职责更清晰，后续更容易扩展。

## 1. 先把真实要求说清楚

Coding Agent 可以调用：

```text
list_directory
list_symbols
search_code
read_file
replace_text
write_file
run_test
```

但它们不应该都具备同样的执行权限。

- `read_file`、`search_code`：在 workspace 边界内通常属于只读。
- `replace_text`、`write_file`：会产生文件系统副作用，V1 必须审批。
- `run_test`：会执行项目代码；只有在可信或适当隔离的环境里，才考虑免除每一次运行前的审批。
- `delete_file`：V1 没有需求，不先暴露该能力。
- 任意 `run_shell`：不加入 V1。

这里的区别不是“模型认为危险不危险”，而是**应用程序定义风险与可用能力**。

## 2. 为什么不只在 Prompt 里写“请先问我”？

因为 `ToolNode` 一旦拿到待执行的 Tool Call，就可能立即调用工具。如果图结构只是：

```text
chat → tools
```

而模型直接提出：

```text
replace_text("main.py", ...)
```

那么图里根本没有一个必须经过人工决策的控制点。

因此我们插入：

```text
chat
  ↓
approval_gate
  ├─ 不需要审批 → tools
  └─ 需要审批 → interrupt() 等待人
                         ├─ 批准 → tools
                         └─ 拒绝 → 记录结果 → chat
```

这样“必须审批”变成代码执行路径中的条件，而不只是 Prompt 的一句提醒。

## 3. Node 和 Edge 的责任

`approval_gate` **不负责修改文件**。它主要完成：

1. 找出这批 Tool Calls；
2. 判断是否涉及受控的写操作；
3. 固定待审批操作的参数与预期修改内容；
4. 必要时暂停，把具体操作交给 UI 展示；
5. 根据审批结果，允许进入受控执行层或记录拒绝。

Edge / Command 负责下一步走哪儿：

```text
允许 → tools
拒绝 → chat 或按策略进入报告
```

如果用户只是拒绝这次对 `main.py` 的修改，回到 `chat` 重新规划是合理的；如果用户明确终止整个任务，就不能再继续尝试其他修改。二者不是同一个意图。

## 4. 理解 `interrupt()`

LangGraph 的人工中断机制通常借助：

```python
from langgraph.types import interrupt, Command
```

节点内：

```python
decision = interrupt({
    "kind": "file_write_approval",
    "path": "main.py",
    "summary": "将错误的减法改为加法",
})
```

执行到 `interrupt` 后，Graph 进入暂停状态。外部 Runner/UI 负责显示审批信息并收集用户决定。

当用户批准时，Runner 用**相同的 thread_id** 继续执行：

```python
graph.invoke(
    Command(resume={"approved": True}),
    config=config,
)
```

拒绝时：

```python
graph.invoke(
    Command(resume={"approved": False}),
    config=config,
)
```

这段是调用机制示意：实际还要校验恢复载荷格式、线程归属及获批内容。`Command(resume=...)` 的值是程序恢复时传回 `interrupt` 的审批数据，而不是在 Chat Model 上随便调用的参数。

## 5. 为什么 Checkpointer 是前提？

如果程序暂停后不知道停在哪个 Node、当前 State 和待审批请求是什么，就没法安全恢复。

常见教学写法：

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {
    "configurable": {
        "thread_id": "coding-task-001"
    }
}
```

`InMemorySaver` 适合本机练习：进程退出后内存数据不会像数据库持久化那样保留。真实应用通常要选合适的持久化 Checkpointer，并保障线程与用户身份的访问控制。

另一个常见错误：恢复时换了 `thread_id`。那相当于跑到另一条线程上，而不是恢复原来的暂停现场。

## 6. 一定把审批放在副作用之前

错误：

```python
write_real_file(path, content)
approved = interrupt({"path": path})
```

这个逻辑先写入再征求同意，已经违背了要求。

正确：

```python
approved = interrupt({"path": path, "content": content})
if approved:
    write_real_file(path, content)
```

但在 LangGraph 中还要注意：**中断后的恢复可能重新进入节点，重新运行其中某些前置代码**。因此不要在 `interrupt` 前放不可重复副作用；对批准后执行的文件操作也要考虑重复执行、当前文件是否发生变化、以及是否需要幂等保护。

把审批独立成 Node 有一个额外好处：审批节点可以尽量保持“无文件写入副作用”，真正写文件的职责留给执行层。

## 7. 用户批准的到底是什么？

这是工程上最重要的细节。

用户看到：

```text
目标文件：main.py

将：
    return a - b

改为：
    return a + b
```

他批准的是**这次具体修改**，不是把以后对整个仓库的所有写权限交给模型。

不能发生：

```text
用户批准修 main.py
       ↓
LLM 重新生成调用
       ↓
工具改写 config.py
       ↓
程序沿用原来的“已批准”状态
```

我们要在审批期间固定待执行的工具名、规范化路径、关键参数和修改内容；执行时核对这些信息仍然与获批请求一致。

高风险操作被批准以后也不意味着可以越过 workspace、文件匹配唯一性或资源上限等硬边界。

## 8. 审批拒绝，为什么可以不新增 approval_status？

我们选择的 V1 策略是：

- 决策流程由 `approval_gate` 控制；
- 审批拒绝作为结果消息返回给模型；
- 本批被拒绝的工具不执行；
- 模型可以重新分析并提出另一方案。

如果审批状态只用于**当前这个 Node 的路由**，不一定有必要增加持久的 `approval_status` State 字段。

可以理解成：

```text
messages → 告诉 LLM 发生了什么
审批节点本地结果 / Command → 决定下一步
```

什么时候新增字段？例如后续流程跨多个 Node 需要结构化查询审批状态，或有严格的审批统计、审计、授权生命周期。那时按需要加入才合理。

## 9. ToolMessage 如何表达“没有执行”？

模型曾经提出：

```python
{
    "name": "replace_text",
    "args": {
        "path": "main.py",
        "old_text": "return a - b",
        "new_text": "return a + b",
    },
    "id": "call_7",
}
```

用户拒绝了它。为了保持工具调用消息关系，我们可以记录：

```python
from langchain_core.messages import ToolMessage

ToolMessage(
    tool_call_id="call_7",
    content="未执行：用户拒绝本次对 main.py 的修改。",
)
```

这个消息**不是工具成功执行的证据**。它是与原调用对应的“未执行结果”。

也不能凭消息字符串就认定文件一定没有变化：真正的执行层应当确保拒绝路径没有发生写入副作用。

## 10. 独立 approval_gate 和 Tool 内审批，哪个绝对正确？

不存在脱离需求的唯一答案。

**Tool 内审批**可以减少 Graph Node 数量，适合简单、局部、固定的写入风险。

**独立 approval_gate**在我们 V1 更合适，因为后面还要考虑：

- 一次 AIMessage 多个 Tool Calls；
- 混合只读和写操作；
- 批量审批；
- 拒绝后为全部调用生成未执行结果；
- 对 Diff、路径和工具参数进行集中展示。

但这也意味着我们必须正确处理 Node 的恢复语义和待执行请求的一致性，而不只是加个漂亮的节点名。

## 11. 本课理解检查

1. 为什么有 `write_file` Tool 不代表模型可以直接调用它？
2. `interrupt` 前为什么不允许发生真正的文件修改？
3. Runner 为什么必须保留原 `thread_id`？
4. 用户批准一次 `main.py` 修改，是否允许下一轮改写 `config.py`？
5. 用户只是拒绝一次修改，为什么可以让 Agent 回 `chat`，但不能无限重复原请求？

下一课：[N12｜多 Tool Calls 批量审批与失败处理](N12-batch-tools.md)。
