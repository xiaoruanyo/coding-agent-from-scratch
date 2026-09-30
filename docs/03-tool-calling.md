# 03. Tool Calling：让 LLM 从“会说”变成“会做”

## 1. Tool 是什么

Tool 是模型可以请求调用的外部能力。

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """计算两个数字的和"""
    return a + b
```

`@tool` 做的是：

> 把普通 Python 函数包装成模型可以理解的 Tool。

它本身不等于 Tool Calling。

## 2. bind_tools

```python
tools = [add]
model_with_tools = model.bind_tools(tools)
```

它的意义是：

> 告诉模型：你现在有这些工具可用。

模型是否调用，仍由模型自己决定。

## 3. tool_calls

模型想调用 Tool 时，AIMessage 中可能出现：

```python
tool_calls=[
    {
        "name": "add",
        "args": {"a": 123, "b": 456},
        "id": "call_xxx",
    }
]
```

注意：

```text
AIMessage.tool_calls
→ 模型提出执行意图

还没有真正执行 Tool
```

## 4. ToolNode

LangGraph 中常用：

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools)
```

它负责：

```text
AIMessage.tool_calls
↓
找到对应 Tool
↓
真正执行
↓
生成 ToolMessage
```

完整链路：

```text
LLM
↓
AIMessage(tool_calls)
↓
ToolNode
↓
Tool
↓
ToolMessage
↓
LLM
```

## 5. Agent Loop

最小 Agent Loop：

```text
            LLM
             ↓
       有 tool_calls？
       /          \
     有            无
     ↓              ↓
 ToolNode          END
     ↓
 ToolMessage
     ↓
    LLM
```

这就是后面 Coding Agent 的核心骨架。

## 6. 一个 AIMessage 可以有多个 tool_calls

例如两个互不依赖的计算：

```text
10 + 20
5 × 6
```

模型可能一次产生：

```text
add(10, 20)
multiply(5, 6)
```

## 7. 独立 Tool 与有依赖 Tool

无依赖：

```text
read_file(a.py)
read_file(b.py)
```

可以考虑并行。

有依赖：

```text
先修改代码
↓
再测试修改后的结果
```

不能把：

```text
replace_text + run_test
```

当成同一批互不依赖动作。

更稳健的模式：

```text
LLM
↓
Tool A
↓
真实结果
↓
LLM
↓
Tool B
```

## 8. tool_call_id

ToolMessage 会通过 `tool_call_id` 和之前的具体 Tool Call 对应。

所以 ToolMessage.content 是：

> Tool 执行的结果。

不是 Tool 函数源码，也不是 Graph State。

## 9. Tool 数量 != Edge 数量

即使有：

```text
read_file
write_file
search_code
run_test
search_memory
...
```

也不需要每个 Tool 单独画一条 Edge。

通常：

```text
LLM
↓
ToolNode
├── read_file
├── search_code
├── run_test
└── ...
```

ToolNode 根据 `tool_calls` 决定真正执行哪个 Tool。

## 10. 核心

> **LLM 负责选择 Tool，ToolNode 负责执行调度，Tool 负责真正产生外部结果，Graph 负责控制整体流程。**
