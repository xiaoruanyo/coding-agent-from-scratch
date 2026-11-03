# Harness 实战课：Tool Calling 的真实执行链路与任务提示词设计

> 课程状态：**已编写教学内容，尚未完成本节产品开发与验收**。课程编号以当前互动课堂为准，不等于教材 Nxx。
>
> 目标：在 Mini Coding Agent 横向工作台中，看见真实的「模型请求工具 → Harness 校验 → 工具执行 → 模型根据工具结果分析」。学习重点是**职责分工、执行证据、任务提示词与验证**，不是记忆 FastAPI / React API。

## 1. 为什么上一节的 AI 分析还不是 Coding Agent？

以前的 `POST /api/llm/analyze` 只接收用户描述。模型无法自动查看 `sample-workspace/calculator.py`，因此即使它给出合理分析，也不能证明它见过实际代码。

要从文本问答升级到工具型 Agent，需要区分四个阶段：

1. **LLM 选择**：收到 Tool 定义后，返回 `AIMessage.tool_calls`。这是请求，不是执行。
2. **Harness 审核**：检查工具名称、参数、路径范围、次数、权限、依赖和超时。
3. **Tool 执行**：程序在边界内读取文件，生成真实结果。
4. **结果回传**：对应的 `ToolMessage(tool_call_id=...)` 发给模型，再由模型生成基于代码事实的回答。

```text
HumanMessage（检查 calculator.py）
    ↓
ChatDeepSeek.bind_tools([read_file])
    ↓
AIMessage(tool_calls=[{name, args, id}])
    ↓
Harness：允许这个 tool 和 path 吗？
    ├─ 不允许 → 明确拒绝并记录证据，不触碰文件
    └─ 允许 → 执行受限 read_file
                    ↓
          ToolMessage(tool_call_id=原调用 id, content=真实结果)
                    ↓
               模型再次调用
                    ↓
            AIMessage(基于结果的分析)
```

**误区**：`bind_tools` 只是让模型认识可调用工具；`tool_calls` 也只是模型生成的请求。工具读取需要应用程序显式执行。Prompt 中写“只读指定文件”不是权限边界，必须用 Tool/Harness 代码验证。

## 2. 系统各层职责（Harness 决策训练）

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| 用户任务 / Prompt | 指定检查目标、允许范围、期望交付 | 直接保证文件访问安全 |
| LLM | 决定是否调用 read_file、提出参数、解释结果 | 实际打开文件、证明真实读取 |
| Harness Guard | 验证名称、参数、工作区、数量、超时等 | 通过模型自然语言臆测执行成功 |
| Tool Executor | 从真实文件系统读取并返回内容/明确错误 | 自主改变任务目标 |
| State / Trace / UI | 记录请求、执行、失败和分析的证据 | 把模型的总结当作 Tool 事件 |

## 3. 课堂中的高质量开发 Prompt：六要素

**目标（Goal）**：看见一个可观察的产品变化，而不是“接入先进 Agent 技术”。

**现状（Context）**：已有 DeepSeek 后端与 React 工作台；本地可能有未提交改动，必须先检查。

**范围（Scope）**：只读教学样例；先用一个 Tool、一个有限执行链路，不加入无限 Agent Loop、写入或 Shell。

**工程约束（Constraints）**：允许路径白名单、路径规范化、文件大小限制、异常隔离、最小修改、保留 M0。

**验收（Acceptance）**：Mock 检查 tool_calls/ToolMessage 对应；非法路径不读；UI 同时显示工具请求与真实执行结果；真实 API 只在明确授权后手动测一次。

**报告（Evidence）**：实际修改文件、关键链路、运行命令与结果、未验证项；不能把 Mock 数据当作真实调用。

### 可以直接发送给 Trae 的任务契约

```text
目标：给现有 Mini Coding Agent 新增“AI 查看代码（只读）”能力。
用户输入“分析 sample-workspace/calculator.py”时，页面应展示：
模型请求 read_file → Harness 校验 → 真实读取结果摘要 → 模型最终分析。
这是新的独立能力，不要替换已有 AI 分析或 M0 固定演示任务。

先检查当前本地 App.tsx、styles.css、后端 llm.py、接口与测试、
以及 sample-workspace 的真实内容；保留所有现有未提交修改。

实现要求：
1. 复用 ChatDeepSeek，通过 LangChain @tool、bind_tools 和消息协议实现
   有限的 LLM → Tool → LLM（本节不要引入 LangGraph）。
2. 只提供一个受控 read_file Tool；允许范围严格限定教学工作区，
   路径规范化后校验边界，拒绝目录穿越、绝对外部路径、符号链接逃逸；
   限制文件读取大小并正确处理不存在的文件。
3. 不允许 write_file、delete_file、Shell 或任意仓库文件执行。
4. 清楚区分 tool_requested、tool_executed、tool_rejected、model_final；
   接口返回必要的非敏感 trace，界面直观展示这些阶段。
5. 保证 ToolMessage 的 tool_call_id 对应原请求；
   模型不调用工具、返回多个工具请求、参数无效、工具异常时有受控处理。
6. 保留现有布局、任务创建、审批、Diff、pytest、SSE 和 AI 分析。
7. 新增 Mock 测试覆盖成功路径、未调用工具、非法路径、工具异常、
   调用 ID 对应、拒绝执行和输出不冒充成功。
8. 运行后端测试、前端构建、浏览器 Mock 验证。
   不自动多次调用收费 API；真实模型验收先给出操作方式，
   由我明确授权后手动执行一次。

交付：列出修改文件、关键消息结构、执行轨迹例子、测试实际结果、
未验证事项；不要报告虚假的“已经读取代码”。
```

### 为什么这样写，而不直接说“给 Agent 加 read_file”？

- “read_file”是一项**实现要求**，不是产品验收口径。必须在 UI 上看见真实链路。
- 先说明现有接口与本地未提交修改，避免 AI 擅自覆盖上一节的横屏布局。
- 将只读和路径校验写成硬边界，避免“模型答应不会乱读”这种伪安全。
- 单独声明不进入 LangGraph，避免一次性把 Tool Calling、状态管理与审批全混起来。
- 把 Mock 与真实 API 的证据等级分开，避免模拟结果冒充真实运行。

## 4. 验收矩阵：先失败，再确认安全

| 用例 | 需要证明的行为 |
| --- | --- |
| 合法文件读取 | 返回真实文件内容或摘要，ToolMessage 正确对应 tool_call_id |
| 非法 `../` 路径 | Guard 阻断，没有发生文件读取 |
| 绝对外部路径 | Guard 阻断 |
| 指向外部的符号链接 | 不可读取外部目标 |
| 文件不存在 | 有可解释的错误，不能报告“已读取” |
| Tool 未调用 | 模型直接回答时明确没有读取文件 |
| 多个 Tool Calls | 限制与处理机制明确，不遗漏需要匹配的 ToolMessage |
| 模型调用失败 | 用户看见错误，Trace 不伪造成功 |
| 现有 M0 | 原有创建任务和审批链路不被覆盖 |

> 安全要在工具执行器与边界逻辑中证明；只在测试中检查一句“请不要读取”不算安全测试。

## 5. 与未来 Harness 工程课程的连接

这一节只解决**一次受控工具调用**。下一节将学习 LangGraph Agent Loop，随后逐步研究：

- Tool Call Guard（工具权限 / 依赖 / 批次）
- Context Builder（搜索优先、局部读取和压缩）
- Checkpoint、审批与恢复（重放与副作用）
- Completion Guard（不能把模型“我完成了”当验证结果）
- 可观测性与 Evals（任务成功率、安全性、耗时和费用）

每完成一节，都应在实际产品里增加一项**能够观察与验证的 Harness 机制**。
