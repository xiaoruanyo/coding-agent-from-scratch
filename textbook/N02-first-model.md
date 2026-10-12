# N02｜第一次调用 Chat Model：`invoke()` 得到的到底是什么？

> 本课目标：跑通一次模型调用，并看懂返回对象的形态。不要着急写 Graph，先理解一次请求里哪些是输入、哪些是模型输出、哪些只是附加元数据。

## 1. 为什么不从 LangGraph 开始？

LangGraph 可以协调复杂流程，但它并不会替我们理解自然语言。无论将来有多少 Node，总有一部分逻辑会调用聊天模型。

如果你还分不清：

```text
HumanMessage
      ↓
model.invoke(...)
      ↓
AIMessage
```

那么看到 `ToolNode`、`MessagesState` 或 `add_messages` 时，就很容易把“模型回复”“工具结果”和“Graph 状态”混为一谈。

我们先让最小链路独立运行，后面再把它封装进 Node。

## 2. 准备一个最小文件

创建 `first_model.py`：

```python
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
model_name = os.getenv("DEEPSEEK_MODEL")

if not api_key or not model_name:
    raise RuntimeError("请先在本地配置 DEEPSEEK_API_KEY 和 DEEPSEEK_MODEL")

model = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url="https://api.deepseek.com",
    temperature=0,
)

response = model.invoke([
    HumanMessage(content="请用一句话解释 LangGraph 是什么")
])

print("回复类型:", type(response).__name__)
print("回复正文:", response.content)
print("是否请求工具:", response.tool_calls)
print("响应元数据:", response.response_metadata)
```

请先运行，成功后观察你的实际输出。由于调用外部服务，输出内容、token 使用量、模型返回的 metadata 都可能不同。

### 逐行理解

`ChatOpenAI` 是 LangChain 提供的一个聊天模型客户端适配类。虽然名称中有 OpenAI，但它也能够用于一些提供兼容 API 的服务；是否完全兼容仍由服务商具体接口决定。

`base_url` 规定发送请求的接口地址。

`model` 是服务端识别的模型名。它不是 LangGraph 的 Node 名，也不是 Python 类名。

`temperature=0` 常用于倾向稳定的输出，但并不保证完全确定性。

`HumanMessage` 明确说明这条输入来自用户。

`model.invoke([...])` 发送一次调用。这里传入消息列表，而不是让模型读取我们 Python 进程里的所有变量。

`response` 通常是一个 `AIMessage` 对象，**不是单纯的字符串**。

## 3. 为什么返回 AIMessage 而不是 str？

因为 Agent 的模型输出不只可能是自然语言，还可能有：

```python
response.content
response.tool_calls
response.response_metadata
response.usage_metadata
```

现在你只需要理解两类：

- `content`：给用户或下一步程序阅读的正文内容。
- `tool_calls`：模型提议调用什么外部工具（目前还没有给模型绑定任何工具，通常为空）。

`response_metadata` 是服务端附带的响应信息，字段随服务商和版本变化。之前的实际学习中，我们曾在 DeepSeek 响应里观察到模型名称、token 使用信息和 prompt cache 等元数据。它们有助于诊断，但**不能把某个固定 metadata 结构当成所有模型都遵守的契约**。

## 4. “模型调用成功”不等于“Agent 任务完成”

假设你把输入改成：

```python
HumanMessage(content="帮我修复当前项目的计算 Bug")
```

模型可能回答你该怎么修，但它并没有自动拿到你的磁盘，也没有自动修改代码。

原因是：我们目前只把一条消息发送给它，并没有给它可执行的文件 Tool，也没有让程序根据 Tool Calls 做事。

区分两个动作：

```text
模型说：“我打算打开 main.py”
        ≠
Python 真正读取了 main.py
```

这条区分将在 Tool Calling、人工审批以及“意图不等于事实”的章节里不断出现。

## 5. SystemMessage 有什么用？

试着加入系统级的行为指导：

```python
from langchain_core.messages import SystemMessage, HumanMessage

response = model.invoke([
    SystemMessage(content=(
        "你是一名代码分析助手。"
        "回答时先区分已知事实与推测。"
        "没有真实执行代码时，不要声称已经完成修改。"
    )),
    HumanMessage(content="修复 Bug 前应该先做什么？"),
])
```

SystemMessage 适合表达稳定的角色、行为原则和约束。但它不是文件系统访问控制，也不能独自实现人工审批。

## 6. 为什么 `invoke` 的结果不是“所有 State”？

这曾是一个典型困惑。这里需要彻底区分三个概念：

1. **模型调用结果** `response`：一次 `model.invoke` 的输出，通常是 AIMessage。
2. **对话消息列表** `messages`：你准备给模型看的若干 HumanMessage / AIMessage / ToolMessage。
3. **LangGraph State** `state`：未来 Graph 执行时由程序管理的结构化数据，除了 `messages` 还可以有 `retry_count`、`test_passed` 等字段。

因此，直接 `print(response)` 不等于打印 Graph 的全部状态；我们现在还没有创建 Graph。

## 7. 看看一次调用里的数据流

```text
代码中的消息列表
    │
    └── HumanMessage("解释 LangGraph")
                  │
                  ▼
             Chat Model
                  │
                  ▼
             AIMessage
              ├── content
              ├── tool_calls
              └── metadata
```

以后加入工具后，可能变成：

```text
HumanMessage
      ↓
AIMessage(tool_calls)
      ↓
Python 执行工具
      ↓
ToolMessage(真实结果)
      ↓
再次调用模型
      ↓
AIMessage(最终解释)
```

请注意：中间“Python 执行工具”这一步，**不会因为模型已经返回 tool_calls 而自动发生**。后面专门讲。

## 8. 常见错误

### 错误一：把 response 当作字符串处理

```python
response = model.invoke(...)
print(response.content)  # 读取正文
```

不要凭直觉认为 `response` 就是原始 `str`。

### 错误二：把 API Key 直接提交进代码

错误做法：

```python
api_key="真实密钥"
```

仓库代码应该从本机私有配置中读取。对已提交的泄露密钥，要撤销并更换。

### 错误三：模型名错误时反复改 LangGraph 边

模型名与认证属于 API 层；Graph 的 Node 和 Edge 还没参与这次调用。

### 错误四：看到 response_metadata 就以为它是 State

metadata 是模型响应附加信息，不是 Graph 自动维护的跨步骤数据。需要用到它时，应明确由程序读取和传递。

## 9. 本课小实验

不用写新程序，只做三次观察：

1. 正常运行最小调用，确认有 `AIMessage` 和正文。
2. 把 `print(response.content)` 与 `print(response)` 对比，想想对象比字符串多了哪些信息。
3. **不要用真实密钥**，暂时让 `DEEPSEEK_API_KEY` 缺失，观察错误发生在代码的哪个阶段：API 请求前还是请求后？

## 10. 理解检查

- `invoke` 的输入为什么经常是一组 Messages？
- `AIMessage.tool_calls` 不为空，代表工具已经真正运行了吗？
- `model.invoke` 返回值与 LangGraph State 有什么区别？
- SystemMessage 能独自保证文件操作权限吗？

答案方向：消息承载上下文；Tool Calls 只是模型提出的意图；模型输出不是完整工作流状态；程序边界不能只靠自然语言提示。

下一课是 **N03｜Messages 与多轮对话**：我们会亲手管理消息历史，理解“模型记住了我”到底意味着什么。
