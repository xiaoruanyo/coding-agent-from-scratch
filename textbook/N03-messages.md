# N03｜Messages 与多轮对话：模型到底有没有“记忆”？

> 前置：完成 N02，知道 `model.invoke` 接受 Messages、返回 AIMessage。本课聚焦消息的语义、多轮调用的本质、ToolMessage 的位置，以及为什么聊天历史不等于 LangGraph State。

## 1. 一个看似简单的问题

用户第一次说：

> 我叫小明。

模型答：

> 你好，小明。

用户第二次问：

> 我刚才叫什么？

为什么有些程序能回答“小明”，另一些却不行？

初学者常把这解释为“模型记住了我”。但在最基本的 API 调用中，更准确的解释是：

**下一次调用有没有把前一次对话作为上下文再次提供给模型。**

模型单次调用并不会天然拥有你程序里过去所有请求的历史。

## 2. 先看两个错误理解

### 错误理解 A：同一个 model 对象就会自动记住

```python
model = ChatOpenAI(...)

model.invoke([HumanMessage(content="我叫小明")])
model.invoke([HumanMessage(content="我刚才叫什么？")])
```

不能假设第二次调用必然知道第一次的内容。这里第二次输入并没有包含“我叫小明”。

### 错误理解 B：只要 print 过内容，模型就看见了

```python
print("我叫小明")
response = model.invoke([
    HumanMessage(content="我刚才叫什么？")
])
```

`print` 是 Python 把内容输出给你的终端，不会自动进入模型 Context。

模型能看到什么，取决于本次调用传给它的内容以及服务端的具体会话机制。我们在这门课使用的显式消息方式里，程序负责管理传入的历史。

## 3. 四类常用 Message

| 类型 | 谁发出的 | 典型内容 | 主要用途 |
|---|---|---|---|
| `SystemMessage` | 系统/应用 | 身份、工作原则、长期约束 | 稳定的行为指导 |
| `HumanMessage` | 用户 | 问题、需求、补充说明 | 用户输入 |
| `AIMessage` | 模型 | 回答、分析结果、Tool Calls | 模型输出 |
| `ToolMessage` | 工具执行层 | 工具结果或未执行原因 | 把外部事实反馈给模型 |

前三个类型比较容易理解，第四个 `ToolMessage` 是 Agent 学习中的关键。

ToolMessage **不是用户的聊天内容**。例如，调用 `run_test` 真正执行 pytest 后，工具结果可以转化为 ToolMessage，供模型下一轮分析。

但模型说“测试已经通过”形成的 AIMessage，并不因为它用了“通过”二字就等价于真实测试结果。

## 4. 一段可运行的两轮对话代码

```python
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

model = ChatOpenAI(
    model=os.environ["DEEPSEEK_MODEL"],
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

messages = [
    HumanMessage(content="我叫小明。请简单打个招呼。")
]

first_answer = model.invoke(messages)
print("第一轮：", first_answer.content)

# 关键：把第一轮模型回复补充到历史
messages.append(first_answer)

# 再补上第二轮用户消息
messages.append(HumanMessage(content="我刚才告诉你我叫什么？"))

second_answer = model.invoke(messages)
print("第二轮：", second_answer.content)
```

这次第二轮的 `messages` 含有：

```text
HumanMessage("我叫小明……")
AIMessage("你好，小明……")
HumanMessage("我刚才告诉你我叫什么？")
```

模型并不是从 Python 隐藏变量里自己挖出名字，而是因为程序把历史重新传给了它。

## 5. 为什么一定要追加第一轮 AIMessage？

除了让模型看到用户说过什么，对话还需要让模型知道**自己之前回答过什么**。

例如：

```text
用户：给我两个方案。
模型：方案 A 是……；方案 B 是……
用户：我选第二个，展开说说。
```

如果只保留两条 HumanMessage，而丢掉模型曾经给出的 A/B 方案，模型就可能不知道“第二个”指什么。

所以，在最基本的多轮调用里，一般保留 HumanMessage 与 AIMessage 的对话顺序。

### 这并不意味着历史越多越好

当 Coding Agent 使用大量工具后，历史可能有：

- 读取几百行源代码；
- 搜索返回几十个命中；
- pytest 输出几千行 traceback；
- 同一文件过期的多个版本；
- LLM 的多轮计划与修复尝试。

把这些原样无限累积并反复发给模型，会带来成本、上下文上限和“旧信息干扰新信息”的问题。后续 `Context Builder` 会解决如何选择、压缩、重新读取。

现在先掌握最基本的规则：**下一轮是否理解上一轮，取决于提供了哪些消息。**

## 6. SystemMessage 应该放什么？

例如 Coding Agent：

```python
SystemMessage(content=(
    "你是一个代码修复助手。"
    "优先观察真实仓库再提出修改。"
    "不要把模型推测当成测试事实。"
))
```

它是指导模型行为的地方，适合：

- 角色与任务定位；
- 稳定的输出约定；
- 倾向性的工作方法；
- 哪些结论必须说明未验证。

不适合无限塞入：

- 当前整个 Repo 的所有代码；
- 每次工具调用的原始日志；
- 每轮动态变化的 `retry_count` 的唯一权威来源；
- 可以由程序强制执行却只写成文字提醒的权限限制。

## 7. ToolMessage 为什么需要 tool_call_id？

一次 AIMessage 可能提出多个工具调用：

```text
call_001 → read_file("a.py")
call_002 → read_file("b.py")
```

工具返回的两个结果必须和原来的调用一一对应：

```python
ToolMessage(
    tool_call_id="call_001",
    content="a.py 的真实内容……"
)

ToolMessage(
    tool_call_id="call_002",
    content="b.py 的真实内容……"
)
```

为什么不用顺序来猜？因为工具可以并行执行，第二个可能先完成。`tool_call_id` 才是明确的关联依据。

**重要协议意识：** 如果一个 AIMessage 含有多个 Tool Calls，下一次继续调用模型之前，需要按照底层提供商和 LangChain 消息协议正确提供每个调用对应的 ToolMessage。某个工具被拒绝或跳过，也要明确表示其没有执行，不能制造假的成功结果。

> 注意：具体服务提供商对工具调用消息的细节可能不同，不能认为可以任意拼接不成对的消息。

## 8. Messages 与 State 为什么不是同一个概念？

以后我们可能定义：

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    test_passed: bool
```

这里 `messages` 只是 State 的一个字段。

`messages` 适合告诉模型发生了什么；`retry_count` 与 `test_passed` 是给程序做精确判断的结构化字段。

举例：

```text
ToolMessage: "pytest 失败了，退出码为 1"
    ↓
sync_state 读取可信测试结果
    ↓
retry_count 从 1 变为 2
test_passed = False
```

ToolMessage 本身不会自动保证 `retry_count` 更新。Graph 里的程序需要负责转换。

### 为什么不让 LLM 自己数重试次数？

因为次数限制是“必须守住的规则”，不应因为历史压缩、模型判断错误或消息遗漏被绕过。由程序计数简单而确定。

## 9. 对话历史、Checkpoint、Memory 也不同

现在我们有三个容易混淆的词：

**Messages**：本次模型请求能读到的消息及其历史组织方式。

**Checkpoint**：Graph Runtime 保存的当前任务现场，可能包含整个 State。它帮助暂停、恢复同一条任务。

**Long-term Memory**：跨任务长期保存和复用的信息，比如稳定的项目约定或经验。它的存储、检索、更新策略要单独设计。

Checkpoint 即使保存了大量历史，也不代表模型的下一次请求就应该全部读取；这正是上下文工程的职责。

## 10. 常见错误与定位

### 只有最新 HumanMessage，没有历史

表现：第二轮模型不知道“我选第二个”的上下文。

定位：检查 `model.invoke` 输入列表，是否包含相关的历史 AIMessage。

### 把 Tool 返回当成 HumanMessage

表现：角色语义混乱，或者丢失工具调用 ID 的关联。

定位：工具结果应通过符合调用协议的 ToolMessage 表达。

### Tool Calls 没有结果就继续调用模型

表现：部分模型服务直接拒绝请求，或模型看到不完整上下文。

定位：检查每个 `tool_call_id` 是否有对应结果/未执行说明。

### 把消息长度等同于“记忆强度”

表现：成本升高、过期代码干扰、模型推理效率降低。

定位：是否混入不需要的旧日志？是否应该按需重新读取源文件？

## 11. 本课复盘

你应该能解释：

1. 为什么同一个 `model` 对象不等于自动保留全部对话？
2. 为什么多轮对话要保留相关的 AIMessage？
3. ToolMessage 与 AIMessage 有什么根本区别？
4. 为什么并行工具执行必须通过 `tool_call_id` 对应结果？
5. `messages` 与结构化 `AgentState` 的关系是什么？

下一课：[N04｜第一次 LangGraph](N04-first-graph.md)。
