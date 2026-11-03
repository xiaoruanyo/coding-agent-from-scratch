# Harness 实战课：Tool Calling 的真实执行链路与任务提示词设计

> 课程状态（2026-11-03）：**Trae 已报告完成 M2 只读 Tool Calling 实现，33 个后端测试通过、前端构建和浏览器 Mock 通过；真实 DeepSeek Tool Calling 尚未验收。** 本文后半部保留最初任务契约及事后复盘。课程编号以当前互动课堂为准，不等于教材 Nxx。
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

## 6. 第 12 课实战复盘（根据 Trae 上传报告，2026-11-03）

**证据等级**：以下内容来自本地 Trae 执行日志与最终报告，未直接审查用户电脑上的全部最终源码，也未代表已经真实调用 DeepSeek。不要将 Mock 测试等同真实模型验收。

### 实际交付

- 新增后端 `tools.py`（read_file schema、Harness 路径与输入校验、文件读取）与 `tool_agent.py`（一次 `LLM → Tool → LLM`）。
- `main.py` 新增 `POST /api/llm/read-file`；原 `llm.py` 复用模型构建与文本提取。
- React 新增「AI 查看代码」入口及「代码查看」Tab，显示模型请求、Harness 判定、工具执行结果和最终模型回答。
- Harness 报告的边界：仅允许 read_file；拒绝多个调用、非法参数、缺少 call_id、绝对/盘符/UNC、`..`、符号链接逃逸；文件 UTF-8 且不超过 16KB。
- 报告的本地测试：后端 **33 passed**（18 原有 + 15 新增），前端 `npm run build` 成功；1920×1080 和 1366×768 视口模拟下，工具记录可内部滚动。
- 真实后端 `/api/health` 200，`/api/llm/read-file` 空白 422；**没有做真实 DeepSeek Tool Calling**。

### 我们在课堂上需要重点理解的边界

1. `AIMessage.tool_calls` 是**请求证据**，不是实际执行证据。
2. `harness.decision=ALLOWED` 是授权判定，仍不等于文件读取成功。需要核对真实 Tool 结果。
3. `ToolMessage.tool_call_id` 必须匹配对应请求；模型最终文字不应代替实际文件读取事实。
4. 对拒绝的调用，程序可选择**明确中止并返回拒绝状态**，不必假装第二次模型调用已发生。UI 第四阶段应明确显示“未产生最终回答”。
5. 只读工具不能只依赖 Prompt 保证；路径、文件类型、大小和符号链接必须在执行边界验证。
6. Mock 是为了验证 UI 和代码分支；真实模型如何选工具存在不确定性，验收时应检查具体 trace，而非只检查 HTTP 200。

### 发现的待改进问题

浏览器验证曾观察到**Mock 因果不一致**：路径穿越或不存在的文件场景里，第一阶段仍显示 `{"path":"calculator.py"}` 和 `call_mock_1`，而后续错误又对应 `../secret.txt` 或 `missing.py`。这不证明生产工具越权，但会误导学习者对原请求/校验/执行链路的理解。

**改进任务 Prompt（建议本节验收后单独完成）**：

```text
请检查 Tool Calling 浏览器 Mock 脚本与代码查看 Trace。
目前越界/不存在文件场景中，tool_call.path 固定显示 calculator.py，
而 Harness/Tool 结果显示了另一个路径。请先定位是 Mock 数据不一致
还是生产接口组装错误；只修改确认有问题的部分。
确保每个测试场景的 tool_call、Harness 判定、Tool 结果一一对应，
并补充断言；不要伪造执行成功或把拒绝显示成模型最终回答。
完成后报告实际测试结果与仍未验证的真实 DeepSeek 路径。
```

### 真实模型最终验收步骤

在确认服务端 Key 可读且后端正在运行的情况下，只进行**一次**手动调用：

```http
POST /api/llm/read-file
Content-Type: application/json

{"instruction":"请先调用 read_file 读取 calculator.py，再依据实际内容说明函数在做什么；不要猜测。"}
```

按顺序检查返回：

- `tool_call.name == "read_file"`，`tool_call.args.path` 指向允许工作区内的教学文件；
- `harness.decision == "ALLOWED"`；
- `file` 反映文件**实际成功读取**；对照当前教学文件内容；
- `final_answer` 与读取的代码一致，前端展示同一事实链；
- 若模型没有请求工具，显示 `NOT_REQUESTED` 不能冒充实际文件读取。

**下一课衔接**：从一次有限的 LLM → Tool → LLM，升级为有最大步数、工具边界、状态记录的 LangGraph Agent Loop，并继续观察真实事件。
