# N07｜Tool Calling：模型“想调用工具”不等于工具已经执行

> 这一课是从聊天模型走向真正 Agent 的分水岭。我们会把 `@tool`、`bind_tools`、`AIMessage.tool_calls`、Python 执行、`ToolMessage` 五个部分逐一拆开。

## 1. 从一个真实需求开始

用户说：

> 帮我计算 123 + 456。

聊天模型也许能自己算对，但 Coding Agent 将来要做的事更多：

- 读取磁盘上当前版本的文件；
- 搜索仓库代码；
- 精确替换字符串；
- 运行真正的测试；
- 获取退出码或超时状态。

这些都不能只靠模型“描述自己做过了”。

因此我们要给模型一套**可以请求**的外部能力，这就是 Tools（工具）。

## 2. 普通 Python 函数与 Tool 的关系

先定义一个普通函数：

```python
def add(a: int, b: int) -> int:
    return a + b
```

Python 可以直接调用：

```python
print(add(123, 456))  # 579
```

但“Python 能调用它”和“LLM 知道它是什么”是两回事。

LangChain 常用 `@tool` 把函数的名称、描述和参数 schema 转换成可以提供给模型的 Tool：

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """计算两个整数之和。"""
    return a + b
```

这里函数签名表达：

- 工具名：`add`
- 参数：`a`、`b`
- 参数类型：整数
- 返回：整数
- 描述：用于计算两个整数之和

Docstring 不只是给人看的注释，它也会成为工具描述的来源之一，影响模型如何决定是否使用 Tool。

## 3. `bind_tools` 到底做什么？

```python
model_with_tools = model.bind_tools([add])
```

你可以把它理解为：

> 将 `add` 这个工具的定义告知模型，使模型有机会以结构化方式提出调用请求。

但它**不是**：

```python
add(123, 456)
```

`bind_tools` 并没有替用户完成加法。

为什么要特别强调？因为 Tool Calling 有清晰的两阶段：

```text
阶段一：模型决定“我要调用哪个工具，以及参数是什么”
                      ↓
阶段二：应用程序根据请求真正执行工具
```

模型输出的是意图，执行发生在 Python 程序里。

## 4. 亲自检查一次 `tool_calls`

```python
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

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

model_with_tools = model.bind_tools([add])

ai_message = model_with_tools.invoke([
    HumanMessage(content="请使用 add 工具计算 123 + 456")
])

print("AIMessage 正文:", ai_message.content)
print("模型提出的 Tool Calls:", ai_message.tool_calls)
```

如果模型选择调用 Tool，可能看到类似：

```python
[
    {
        "name": "add",
        "args": {"a": 123, "b": 456},
        "id": "call_abc123",
        "type": "tool_call",
    }
]
```

这里的 `call_abc123` 只是讲解用的示例 ID；实际 ID 由服务返回。

**不能假设所有模型、所有 Prompt 都必然触发工具调用。** 我们可以查看真实的 `ai_message.tool_calls` 再决定下一步，而不是因为用户说了“使用工具”就跳过判断。

## 5. `tool_calls` 还没有计算出 579

假设模型输出了：

```python
{"name": "add", "args": {"a": 123, "b": 456}}
```

模型只是说：“我希望程序执行 add(123,456)。”

此时 **add 函数还没有执行**。

我们可以写显式的执行逻辑。为了保持教学清楚，以下仅针对一个已知 `add` 工具演示：

```python
if not ai_message.tool_calls:
    print("模型没有请求工具，正文是:", ai_message.content)
else:
    for call in ai_message.tool_calls:
        if call["name"] != "add":
            raise ValueError("不允许执行未知工具")

        args = call["args"]
        result = add.invoke(args)

        print("Python 真正执行的结果:", result)
```

关键分界线在：

```python
result = add.invoke(args)
```

这行才是真正运行了 Tool。

在正式 Coding Agent 里，绝不能把模型给出的任意名字直接当成可以执行的 Python 函数或 Shell 命令。必须有明确的工具白名单、参数校验和权限边界。

## 6. ToolMessage 如何把结果送回模型？

模型还需要知道工具实际返回了什么，才能对用户给出基于事实的总结。

```python
from langchain_core.messages import ToolMessage

call = ai_message.tool_calls[0]
result = add.invoke(call["args"])

tool_result = ToolMessage(
    content=str(result),
    tool_call_id=call["id"],
)
```

接下来：

```python
from langchain_core.messages import HumanMessage

messages = [
    HumanMessage(content="请使用 add 工具计算 123 + 456")
]

# 模型的工具调用请求也要保留在消息历史
messages.append(ai_message)

# 工具真实执行后的响应，与请求 ID 对应
messages.append(tool_result)

final_answer = model_with_tools.invoke(messages)
print(final_answer.content)
```

这里模型得到一个完整的最小链路：

```text
HumanMessage("请计算")
           ↓
AIMessage(tool_calls=[add(123, 456)])
           ↓
Python 调用 add
           ↓
ToolMessage(content="579", tool_call_id=...)
           ↓
AIMessage("123 + 456 = 579")
```

如果下一轮模型又提出 Tool Calls，那程序需要继续处理；不能假设一次工具调用之后一定得到最终自然语言答复。这就是后面要实现的 **Agent Loop**。

## 7. Function Calling 与 Tool Calling 有什么关系？

你可能看到多个术语：

- Function Calling：很多模型 API 使用的能力名称，表示模型以结构化方式要求调用函数或工具。
- Tool Calling：更加通用的“模型请求使用某项工具”概念。
- `@tool`：LangChain 中定义工具的一种接口。
- `bind_tools`：把工具定义绑定给模型的方法。
- `tool_calls`：模型输出的结构化调用请求。
- `ToolNode`：LangGraph 里用于处理工具调用的预构建执行节点。
- MCP：外部工具与上下文能力的连接协议生态，不是 `@tool` 的同义词。
- Skill：可复用的能力说明或工作流程封装，具体语义依赖使用它的 Agent 平台。

这些东西属于不同层次，不能互相替换：

```text
Tool 能力
   ↑ 对模型说明
@tool / bind_tools
   ↑ 模型提出调用
AIMessage.tool_calls
   ↓ 程序实际执行
Tool / ToolNode
   ↓ 真实结果
ToolMessage
```

## 8. “多个 Tool Calls”为什么重要？

模型一次可能输出：

```python
[
    {"name": "add", "args": {"a": 10, "b": 20}, "id": "call_1"},
    {"name": "add", "args": {"a": 30, "b": 40}, "id": "call_2"},
]
```

两次相加互不依赖，程序可以选择并行执行。

但：

```text
先 replace_text 修改文件
       ↓
再 run_test 验证新代码
```

存在依赖关系，不能简单假设一次批量调用已经包含可靠的顺序。

Tool Calling 负责表达调用请求。**依赖、审批、串行/并行、失败后停止，属于执行层和 Harness 的设计问题。**

## 9. 最常见的错误

### 看见 tool_calls 就说“工具已经运行”

错误。只有 Tool 执行器真的调用了工具，并产生可信结果，才能说已经执行。

### 让模型决定可执行的任意工具名

错误。模型输出不应直接映射到任意 Python 属性、Shell 命令或未授权文件操作。

### ToolMessage 没带正确的 ID

即使 Tool 成功返回 579，如果消息没有与原 Tool Call 正确关联，下一次模型请求仍可能不符合工具调用协议。

### 把模型生成的工具参数当作可信输入

工具参数是模型提出的请求，仍需校验。例如文件路径可能越界，替换文本可能不唯一，测试命令可能被注入不允许的参数。

## 10. 本课理解检查

1. `@tool` 与 `bind_tools` 分别做了什么？
2. `AIMessage.tool_calls` 不为空，说明 Python 里的工具已运行了吗？
3. 谁负责把调用请求匹配到允许的 Tool？
4. `ToolMessage` 为什么需要 `tool_call_id`？
5. 一次模型调用给出多个 Tool Calls，就自动保证执行顺序吗？

下一课：[N08｜ToolNode 与 Agent Loop](N08-toolnode-loop.md)。
