# 01. LangChain 最小基础：先学会和模型说话

## 1. 为什么先学最小版 LangChain

LangGraph 负责流程编排，但真正调用大模型、组织消息、定义 Tool 时，经常会用到 LangChain 的基础对象。

我们不需要先把 LangChain 全学一遍，只学后面构建 Agent 必需的部分：

```text
Chat Model
Messages
Tool
Tool Calling
```

## 2. 调用一个 Chat Model

课程实践中使用过：

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key="...",
    base_url="https://api.deepseek.com",
)
```

调用：

```python
from langchain_core.messages import HumanMessage

response = model.invoke([
    HumanMessage(content="一句话解释 LangGraph")
])

print(response.content)
```

重要理解：

```text
model.invoke(...)
→ 输入 Messages
→ 返回 AIMessage
```

不是单纯返回字符串。

## 3. 四种最常见 Message

```python
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
```

### HumanMessage

用户给模型的信息。

### AIMessage

模型返回的信息。

它除了 `content`，还可能带：

```python
tool_calls=[...]
```

### SystemMessage

用于放系统规则、角色、工作原则等。

例如：

```text
你是 Coding Agent。
修改代码时优先最小改动。
不要宣称未验证的结果已经成功。
```

### ToolMessage

Tool 执行完成后，把真实结果送回模型。

例如：

```text
AIMessage:
我要调用 add(123, 456)

ToolMessage:
579
```

## 4. 多轮对话本质

多轮不是模型“自己永久记住”。

而是下一次调用时继续把历史 Messages 传进去：

```python
messages = [
    HumanMessage(content="我叫小明"),
    AIMessage(content="你好，小明"),
    HumanMessage(content="我叫什么？"),
]

response = model.invoke(messages)
```

所以：

> 模型能“记住”多少，取决于当前 Context 里给了它什么。

这会直接引出后面的 Context Engineering。

## 5. System Prompt 的作用

System Prompt 更适合放：

- 稳定的身份；
- 长期行为规则；
- 基本安全原则；
- 工具使用原则。

不要把所有动态工作数据都塞进 System Prompt。

后面我们会把：

```text
Working Summary
Memory
Recent Messages
Repo Context
```

和稳定规则分开。

## 6. 本章要掌握什么

不要求背所有类。

只需要能看懂：

```text
HumanMessage
→ 用户

AIMessage
→ 模型

SystemMessage
→ 系统规则

ToolMessage
→ Tool 的真实执行结果
```

以及：

> Chat Model 的一次调用，本质是在当前 Context 中读取一组 Messages，再产生新的 AIMessage。
