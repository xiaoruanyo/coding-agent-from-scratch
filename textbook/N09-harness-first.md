# N09｜Agent Harness 到底是什么？为什么不能只写一个很长的 Prompt？

> 这一课来自一段很重要的学习疑问：“Harness 我一直听你提到，但我理解的只是 Agent 的内部设计，包括提示词和安全边界，是这样吗？”  
> 答案是：这个理解接近，但**Harness 不等于 Agent 的所有内部东西**，也不等于 LangGraph 本身。

## 1. 先给一个工程上可用的定义

**Agent Harness（Agent 运行控制框架/工程支撑层）**：围绕模型建立的执行、权限、状态、上下文、验证和恢复机制，让 Agent 的行为在现实环境里更可靠。

Harness 不是 LangGraph 官方某个固定类名，也不是要求所有团队采用同一套架构的标准。它是讨论 Agent 工程化时的一种职责集合。

你可以记住：

```text
LLM：决定“应该做什么”
Tool：负责“实际做了什么”
Harness：保障“能怎样做、做错了怎么办、何时能结束”
```

真实系统里，LLM 和工具常被 Harness 包围并协调，但不要把 Harness 理解成一个必须独立部署的大型服务。

## 2. 一个只有 Prompt 的 Coding Agent

假设用户说：

> 修复当前项目 Bug，写文件要经我同意，普通测试失败最多 3 次，最终必须告诉我是否真实测试通过。

你写了一个非常清楚的 System Prompt：

```text
你是一名严谨的 Coding Agent。
先搜索，再读取代码；优先最小修改。
写文件前必须向用户确认。
测试失败最多重试三次。
没有测试成功不能报告成功。
```

它能帮助模型理解你的期望，但仍有风险：

**权限风险**：如果 `write_file` 这个工具只要收到参数就直接修改，模型完全有可能在某次工具调用里绕过“先问人”。

**计数风险**：模型也许把一次 timeout 算成普通测试 FAIL，也可能忘记之前失败几次。

**事实风险**：模型认为自己修好了代码，但真实 pytest 仍然失败。

**执行风险**：模型一次要求先写文件、再测试。如果写入失败，测试是否还应该执行？

所以需要程序层面的保证。

## 3. 把四件事拆开看

| 需求 | 模型能参与什么 | Harness 要保证什么 |
|---|---|---|
| 找到 Bug | 分析症状、搜索关键词、选择文件 | 搜索与读取不会越界、输出有上限 |
| 修改代码 | 提出精确修改方案 | 写操作在副作用前审批，批准绑定具体内容 |
| 测试失败继续修复 | 分析错误、决定下一次修法 | 普通失败次数精确计数，timeout 另行处理 |
| 最终汇报 | 总结修改与验证 | 没有真实测试成功不能标记 SUCCESS |

你会发现 Harness 不是替代模型思考 Bug 根因，而是把**必须确定**的事情落在程序里。

## 4. Harness 可以包含哪些东西？

### Prompt 与角色约束

模型应该遵循什么工作习惯、怎样汇报未知信息。

但 Prompt 是行为引导，不是可靠的硬权限检查。

### Graph / Workflow

```text
chat → approval_gate → tools → sync_state → completion_guard
                       ↑                      │
                       └───── 需要继续 ────────┘
```

这条链路规定哪些步骤必经，哪些地方能分支和停止。

### Tool 的硬边界

即使模型要求：

```python
read_file("../../private.txt")
```

工具也应拒绝工作区外路径。这里不是“用户是否同意”问题，而是 Tool 的能力边界。

### State 与事实同步

```python
retry_count = 2
test_passed = False
last_error_type = "TEST_FAIL"
```

这些供程序判断的状态，不能只让模型从自然语言里猜。

### 审批与 Runner

Graph 使用 `interrupt` 发出待审批事件，Runner/UI 把具体变更展示给人，使用相同 thread_id 恢复。

### Checkpoint 与 Context Builder

Checkpoint 保存当前任务现场；Context Builder 选择模型当前看到什么。这两件事不同：**保存了历史，不代表每次都应该把历史全部发给模型。**

## 5. Harness 与 Workflow 的关系

一个很常见的误解是“我的 LangGraph 图就是 Harness”。

不完全对。

```text
Harness
├── Workflow / Graph
├── State / Checkpoint
├── Prompt / Context 组织
├── Tool 执行器与资源边界
├── 审批机制
├── 错误分类与重试机制
├── 完成条件 Guard
└── Runner / 观测 / 恢复
```

Workflow 是“先后执行哪些步骤、怎么分支”的部分。

下面这些规则即使很重要，也不一定需要成为独立 Node：

- `read_file` 最多读 200 行；
- `search_code` 最多返回 20 个结果；
- `run_test` 单次最多运行 30 秒；
- `replace_text` 的 `old_text` 必须唯一匹配；
- 不能越出 workspace。

它们更适合在工具执行层以代码强制。

## 6. 为什么模型越强，Workflow 反而可以更薄？

考虑两种设计。

### 设计 A：把探索路径写死

```text
固定先读 README
→ 固定搜 error
→ 固定读第一个文件
→ 固定查 test 目录
→ 固定尝试修改
```

不同项目的最佳探索路径并不一样。随着模型能力变强，过多固定步骤可能让模型无法发挥判断能力。

### 设计 B：保留必需规则，把探索权交给模型

```text
LLM 自己决定搜索什么、读什么、怎么修
    │
    ├─ Tool 保证权限与输入限制
    ├─ 审批层保证写入前获得批准
    ├─ State 保证失败次数准确
    └─ 完成条件要求真实测试通过
```

模型越强，可以少写一些僵硬的“固定探索流程”，但**安全边界和系统不变量不能随模型能力增强而消失**。

这是我们设计 V1 的主要原则。

## 7. Tool 的能力边界与 Graph 的任务规则

这个区别非常重要。

### Capability Boundary（单次能力边界）

与当前任务经历了多少轮无关，每次调用都必须成立：

```text
文件路径不能越 workspace
read_file 单次最多 200 行
replace_text 旧文本必须精确且唯一匹配
run_test 单次不得无限运行
```

最适合 Tool 层。

### Workflow Policy（跨步骤业务规则）

需要知道整个任务目前经历了什么：

```text
普通测试失败累计最多三次
测试通过才能标记成功
某种错误类型必须终止自动修复
```

最适合 State + Graph Guard。

**一个简单判断**：如果同一个 Tool 被别人单独调用时也必须遵守的限制，通常属于 Tool 的硬边界；如果限制依赖整个任务累计情况，通常属于 Workflow Policy。

## 8. Harness 不应该越做越厚

不要因为课程讲了很多机制，就把每个操作都拆成一个 Node。

例如：

```text
模型生成搜索关键词
→ 独立词语清洗 Node
→ 关键词验证 Node
→ 搜索策略 Node
→ 搜索调用 Node
→ 搜索结果整理 Node
```

如果这些步骤没有独立路由、重试、审批、安全或观测需求，就可能只是徒增复杂度。

拆 Node 的有力信号包括：

- 要在中间做分支；
- 要独立 Retry；
- 要独立 `interrupt`；
- 具有独立权限；
- 必须单独观测和统计；
- 不同阶段要给模型不同能力。

即使两个函数很短，只要责任边界重要，也可能值得拆。反之，代码很多也不意味着每十行必须一个 Node。

## 9. 一个常见“过度工程化”的反例

为了记录所有东西，在 State 中增加：

```python
current_file: str
last_search: str
all_files_read: list[str]
last_model_reasoning: str
planned_patch: str
last_tool_output: str
test_passed: bool
retry_count: int
...
```

结果是：

- 同一信息在 Messages 和 State 重复；
- 原始代码后来改了，但字段还是旧版本；
- 每个 Node 都要维护大量同步；
- 很难判断哪个字段是可信事实。

State 不是日志。是否加入字段，要看后面的程序是否真的**可靠地读取它做判断**。

## 10. 把本课映射到我们的 Coding Agent V1

我们已经讨论过的 V1 设计：

```text
LLM chat
  ↓
approval_gate
  ↓
tools
  ↓
sync_state
  ↓
completion_guard
  ↓
final_report
```

这里：

- `chat` 负责模型的动态判断；
- `approval_gate` 负责审批控制；
- `tools` 负责执行真实工具；
- `sync_state` 负责把外部测试结果转成结构化事实；
- `completion_guard` 负责是否成功、继续或停止；
- `final_report` 负责真实汇报，但没有新的工具执行权。

这不是唯一正确的图，而是对 V1 需求的一种相对清晰的职责划分。

## 11. 练习：强模型来了之后保留什么？

假设未来 LLM 能非常准确地定位 Bug：

A. 一段复杂的“按固定步骤探索代码”的 Prompt。  
B. 修改文件之前的人工审批机制。

哪一个更可能简化，哪一个仍然应该保留？

参考：A 可能因模型能力增强而简化；B 属于权限和副作用安全边界，不应该只因为模型变强就撤销。

## 12. 本课核心

> **Harness 不是“让 Agent 看起来复杂”，而是把那些不能仅靠 LLM 自觉完成的工程保证落实下来。**

> **LLM 负责聪明，程序负责靠谱。**

下一课：[N10｜Tool 结果与结构化 State](N10-sync-state.md)。
