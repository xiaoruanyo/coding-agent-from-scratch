# 原课程课号 → 新教程章节映射

早期课程是边学边演进的，因此新仓库不机械保留 75 个碎文件，而是按知识体系重新组织。

| 原课号 | 主题 | 新章节 |
|---|---|---|
| 1～约 15 | State / Node / Edge / Conditional Edge / Loop / Reducer | 02 |
| 约 16～26 | LangChain 最小基础、Messages、Tool Calling、多 Tool | 01、03 |
| 27～28 | ToolNode 实际链路、DeepSeek Agent Loop | 03 |
| 29 | write_file 人工审批 | 05 |
| 30～32 | sync_state、Graph 重试控制、final_report | 04、13 |
| 33～35 | State 设计、职责边界、Capability vs Workflow Policy | 10 |
| 36～37 | Tool vs Node、Node 拆分粒度 | 09 |
| 38～43 | search_code、bounded read、replace_text、Context 基础 | 06 |
| 44～45 | Tool Error Handling / Recovery | 08 |
| 46 | Command | 07 |
| 47～52 | Subgraph、State channel、Checkpoint | 07 |
| 53～54 | Parallel / Superstep / Send / Reducer | 07 |
| 55 | RetryPolicy | 08 |
| 56 | Stream | 08 |
| 57～58 | 正常失败 vs 异常、Runner、审批粒度 | 08 |
| 59 | Stream + Runner 完整循环 | 08 |
| 60～61 | Completion Guard 与防死循环 | 09 |
| 62 | Tool Call Guard / 有依赖 Tool 顺序 | 09 |
| 63 | Retry / Loop / Recovery | 08 |
| 64～65 | 薄 Harness、从需求反推职责 | 09 |
| 66 | 意图 vs 事实 | 10 |
| 67 | State 最小化 | 10 |
| 68 | Context 膨胀与压缩 | 11 |
| 69 | Working Summary vs Memory | 11 |
| 70 | Context Builder | 11 |
| 71 | Repo Map / Keyword Search / RAG / Bounded Read | 12 |
| 72 | Python AST 最小 Repo Map | 12 |
| 73 | 分层 Repo Map / 渐进式展开 | 12 |
| 74 | 过期上下文 / 重新观察真实环境 | 11 |
| 75 | Coding Agent V1 Context 策略收口 | 11、13 |
| 76 起 | Coding Agent V1 架构设计与毕业项目 | 13、ROADMAP |

> 课号不是知识边界。新教程以“读完一章能形成完整心智模型”为优先。
