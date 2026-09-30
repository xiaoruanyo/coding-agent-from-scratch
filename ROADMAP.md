# 后续路线

## 当前阶段：Coding Agent Core 收口

接下来重点不是继续无限增加新概念，而是把已有知识组合成一个完整 Agent。

```text
Repo Context
↓
Context 策略
↓
完整 V1 架构设计
↓
从空目录完成毕业项目
↓
工程化拆分
```

## 毕业项目

毕业项目采用“分级提示”方式。

第一阶段只提供：

- 需求；
- 可使用的知识点；
- 验收标准。

如果卡住，可以逐级获得提示：

```text
一级提示
→ 只提醒思考方向

二级提示
→ 提醒应该使用哪类机制

三级提示
→ 给局部伪代码

仍然解决不了
→ 一起完成实现
```

目标是自己决定：

- State 放什么；
- Tool 有哪些；
- Node 怎么拆；
- Graph 有哪些硬规则；
- Runner / UI 负责什么。

## Core 完成后的扩展

### LangChain 高层能力

在已经亲手理解 Agent Loop 和 Harness 后，再学习高层 Agent 封装，重点理解“框架替我们做了什么”。

### 工程化拆分

```text
agent/
├── state.py
├── tools.py
├── nodes.py
├── routes.py
├── graph.py
└── prompts.py

runtime/
└── runner.py

main.py
```

### 产品化

```text
Coding Agent Core
↓
FastAPI
↓
React + Vite
↓
Stream / Diff / Approve / Test Status
↓
Mini Codex 风格 UI
```

前端作为扩展篇，不把主课程变成完整前端课。
