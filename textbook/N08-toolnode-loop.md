# N08｜ToolNode 与 Agent Loop：让“模型→工具→模型”真的循环起来

> 前置：完成 N07。本课的目标不是把所有 Coding Agent 功能塞进一张图，而是理解 **LLM 产生 Tool Calls → ToolNode 执行 → ToolMessage 反馈 → 再次调用 LLM** 的闭环。

## 1. 我们上一课还缺什么？

N07 的手动演示里，我们必须自己写：

```python
if call["name"] == "add":
    result = add.invoke(call["args"])
```

未来有：

```text
list_directory
search_code
read_file
list_symbols
replace_text
write_file
run_test
```

难道每增加一个 Tool，就一定要在 Graph 上新增一个同名 Node，再为它画一条 Edge？

没有必要。

模型负责提出使用哪个 Tool 的请求；一个统一执行节点可以根据名称找到已登记的 Tool 并执行。LangGraph 提供了 `ToolNode` 来承担常见的工具执行流程。

## 2. 最小 ToolNode

```python
from langgraph.prebuilt import ToolNode

tools = [add]
tool_node = ToolNode(tools)
```

它的常见职责：

```text
收到上一条 AIMessage.tool_calls
              ↓
查找匹配的已注册 Tool
              ↓
执行实际 Tool
              ↓
返回对应 ToolMessage
```

重要区别：

- `@tool`：定义 Tool。
- `bind_tools`：把 Tool schema 提供给模型。
- `ToolNode`：运行时执行模型请求的 Tool。
- `ToolMessage`：将真实执行结果交回模型。

## 3. 先看完整 Graph 的形状

```text
           ┌──────────┐
           │   chat   │
           └────┬─────┘
                │
        有没有 tool_calls？
         /             \
       有               没有
       │                 │
       ▼                 ▼
   ┌───────┐            END
   │ tools │
   └───┬───┘
       │
       └──────────→ chat
```

这里只包含两个实际 Node：

- `chat`：调用模型并更新 messages。
- `tools`：执行 Tool Calls 并更新 messages。

有没有 Tool Calls 是**条件边的路由逻辑**，不需要给每个 Tool 造一个 Graph Node。

## 4. 完整示例：使用 add 工具

```python
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

@tool
def add(a: int, b: int) -> int:
    """计算两个整数之和。"""
    return a + b

model = ChatOpenAI(
    model=os.environ["DEEPSEEK_MODEL"],
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

tools = [add]
model_with_tools = model.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def chat_node(state: AgentState):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def route_after_chat(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "finish"

builder = StateGraph(AgentState)
builder.add_node("chat", chat_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "chat")
builder.add_conditional_edges(
    "chat",
    route_after_chat,
    {
        "tools": "tools",
        "finish": END,
    }
)
builder.add_edge("tools", "chat")

graph = builder.compile()

result = graph.invoke(
    {
        "messages": [
            HumanMessage(content="请使用 add 工具计算 123 + 456，给出最终结果")
        ],
    },
    config={"recursion_limit": 15},
)

for message in result["messages"]:
    print(type(message).__name__, message.content)
```

**版本说明：** 这段示例按本课程的 LangGraph / LangChain 调用模式编写；不同版本和模型服务可能存在响应差异。课堂验收不是要求模型一定生成完全相同的字句，而是检查实际的 Tool Calls、ToolMessages 与最终内容。示例需要真实 API Key 才能运行。

## 5. 一轮真实数据流应该怎样读？

理想的典型流程（具体模型是否选择工具仍需看真实输出）：

**第一步：人类提出问题。**

```text
HumanMessage:
请使用 add 工具计算 123 + 456
```

**第二步：chat 调用 LLM。**

返回：

```text
AIMessage:
tool_calls = [
  {"name":"add","args":{"a":123,"b":456},"id":"call_1"}
]
```

这条 AIMessage 可能没有完整自然语言答案，但它具有结构化的 Tool Call。

**第三步：条件边判断。**

```python
if last_message.tool_calls:
    return "tools"
```

所以 Graph 进入 ToolNode。

**第四步：ToolNode 执行 add。**

真实调用结果为 `579`，写入与调用 ID 对应的 ToolMessage。

**第五步：回到 chat。**

```python
builder.add_edge("tools", "chat")
```

下一次 LLM 调用能看到：

```text
HumanMessage(原始问题)
AIMessage(tool_calls=[...])
ToolMessage(579)
```

于是它可以基于真实结果组织最终回答。

**第六步：没有新的 Tool Calls。**

条件边选择 `finish`，Graph 走到 END。

## 6. 为什么需要 `add_messages`？

我们在 State 中写：

```python
messages: Annotated[list, add_messages]
```

然后 `chat_node` 只返回：

```python
return {"messages": [response]}
```

ToolNode 也返回新的工具消息更新。

Reducer 负责将这些消息与已有历史合并，使下一轮 LLM 看到必要的对话和工具反馈。

如果不用合适的消息合并策略，新消息就可能覆盖旧消息，导致下一轮缺失工具调用与原始问题。

这也是前一课 Reducer 在真实 Agent 中最直接的用途之一。

## 7. 一次 AIMessage 有多个 Tool Calls 会怎样？

例如：

```text
AIMessage:
  call_1: add(10, 20)
  call_2: add(30, 40)
```

执行层需要为每个调用产生对应的结果：

```text
call_1 → ToolMessage(30)
call_2 → ToolMessage(70)
```

不能只给一个 `ToolMessage("100")`，然后把两个原始调用丢掉。

更重要的是，常规 ToolNode **不等于**我们自己设计的所有执行策略：

- 不自动保证“高风险操作先审批”的业务要求；
- 不自动代表“修改成功才能运行后续测试”的依赖约束；
- 不替代任务级 retry_count 和完成条件；
- 不意味着模型输出天然可信；
- 不表示可以任意顺序混合并行读、写与测试。

这些会在 Coding Agent V1 的 Harness 章节进一步展开。

## 8. 为什么示例在没有 Tool Calls 时可以 END，毕业项目却不行？

对于“加法工具”的最小 Agent Loop，模型没有工具调用请求时结束是合理的教学简化。

但 Coding Agent V1 的要求是：

> 测试没有真实通过，不能以成功状态结束。

假设模型没有产生 Tool Calls，却说“代码已经修好”。如果 Graph 直接 END，就可能产生未验证的完成声明。

因此在毕业项目中我们要改成：

```text
chat 没有 Tool Calls
        ↓
completion_guard
        ↓
检查 test_passed / error_type / retry_count 等事实
        ↓
继续、失败报告或成功报告
```

**同一张最小教学图的结束条件，不等于真实产品中合格的 Completion Guard。**

## 9. 给 ToolNode 加 RetryPolicy 可以解决全部错误吗？

不能。

例如 Tool 列表中同时包含 `read_file` 与 `replace_text`：

- read_file 失败也许可以安全地重试；
- replace_text 可能已经发生了部分副作用；
- 重复写入可能覆盖新的文件状态。

因此不应该无差别地给整批有副作用的工具重试。要区分执行异常、业务失败、幂等性与具体的工具责任。

## 10. 练习：预测调用顺序

如果模型连续两轮都返回了 Tool Calls，Graph 的 Node 执行顺序是什么？

参考：

```text
chat
 → tools
 → chat
 → tools
 → chat
 → END（最后一轮无新的 Tool Calls）
```

这不是无限递归的 Python 函数调用，而是图根据条件边与普通边重复调度节点。

## 11. 本课小结

现在你应当能准确说出：

- ToolNode 是执行模型所提 Tool Calls 的节点，而不是模型本身。
- add_messages 合并消息更新，使 LLM 能看到工具的真实反馈。
- 模型可以连续提出多轮 Tool Calls，构成 Agent Loop。
- “没有 Tool Calls 就 END”只是最小图的简化结束规则。
- Coding Agent 需要额外的审批、执行边界、State 同步与 Completion Guard。

**接下来：** 进入 State / Checkpoint / 人工审批篇。我们会先学习 [N09｜Harness 为什么存在](N09-harness-first.md)，建立以后每个安全机制的归属。
