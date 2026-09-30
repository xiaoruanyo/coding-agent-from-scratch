# Examples：最小可运行示例

这里用于存放每个关键知识点的最小示例。

建议保持原则：

> 一个示例只说明一个核心问题，不把所有 Agent 能力都塞进一个文件。

计划结构：

```text
examples/
├── 01_minimal_llm.py
├── 02_basic_graph.py
├── 03_tool_calling.py
├── 04_agent_loop.py
├── 05_checkpoint.py
├── 06_interrupt.py
├── 07_parallel_send.py
├── 08_retry_stream.py
└── 09_context_builder.py
```

完整 Agent 不放这里，最终工程放在：

```text
coding-agent/
```

后续课程运行并验证代码时，再逐步把对应最小示例补进来，避免为了“目录看起来完整”提前放未经验证的代码。
