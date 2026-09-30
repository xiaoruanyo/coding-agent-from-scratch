# Coding Agent：最终综合项目

这个目录用于最终毕业项目。

教程前半段的代码以“看清机制”为优先；这里则会逐步从单文件 Demo 走向工程化 Agent。

## 目标能力

```text
用户提出代码任务
↓
Agent 探索 Repo
↓
搜索 / 读取代码
↓
分析并提出修改
↓
人工审批
↓
最小范围写入
↓
运行 pytest
↓
失败 → 继续修复
异常 → Retry / Recovery
↓
满足完成条件
↓
最终报告
```

## V1 组件

### Tools

```text
list_files / list_directory
list_symbols
search_code
read_file
replace_text
write_file
run_test
```

### State

V1 会根据真实 Graph 需求逐步确定，不为了“完整”提前堆字段。

核心候选：

```text
messages
retry_count
test_passed
last_error
last_error_type
working_summary
premature_finish_count
modified_files
```

### Harness

```text
workspace boundary
write approval
max retries
Completion Guard
Tool Call Guard
Recovery boundary
Context strategy
```

### Runtime

```text
Checkpointer
thread_id
stream
Runner
interrupt / resume
```

## 工程化目标结构

后续从单文件版本重构为：

```text
coding-agent/
├── agent/
│   ├── state.py
│   ├── tools.py
│   ├── nodes.py
│   ├── routes.py
│   ├── graph.py
│   └── prompts.py
├── runtime/
│   └── runner.py
├── sandbox/
├── tests/
└── main.py
```

不要一开始过度拆分。

教程会先保留一个完整单文件版本，让整条执行链可见；确认理解后再做“从 Demo 到工程化”的重构。

## 毕业项目规则

最终主体由学习者从空目录设计完成。

可以获得分级提示，但不会直接复制课程中的完整 Agent。

验收重点：

- 能正确划分 LLM / Tool / State / Graph / Runner；
- 有安全边界；
- 有真实验证；
- 能处理正常失败与执行异常；
- 不会因为 LLM 提前结束就错误宣称成功；
- 长任务 Context 有基本控制；
- 代码结构可继续扩展。
