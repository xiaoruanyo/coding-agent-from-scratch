# 09. Agent Harness：只把“必须确定”的东西确定下来

## 1. 什么是 Harness

这里把 Harness 理解成：

> 围绕 LLM 的执行框架、规则、权限、状态和可靠性机制。

它不是为了取代模型思考，而是让 Agent：

- 不越过安全边界；
- 不无限循环；
- 不因为模型一句“完成了”就真的结束；
- 不把有依赖的动作乱并行；
- 出错时有可控行为。

---

## 2. 最重要的总原则

> **模型越强，Workflow 应该越薄；但安全边界和系统不变量不能因为模型变强而消失。**

不要把模型已经很擅长的事情写死：

```text
先读 A
再读 B
再搜 C
再看 D
```

更合理：

```text
LLM
→ 决定读什么、搜什么、怎么修

Harness
→ 守住权限、资源、结束条件、次数和依赖规则
```

---

## 3. 三层职责

### 系统不变量

```text
workspace 边界
危险操作审批
用户拒绝后不能继续执行
资源上限
最大文件数
```

→ Tool / Code / Harness

### 可靠性机制

```text
RetryPolicy
Checkpoint
最大循环次数
错误分类
完成条件
```

→ Runtime / Graph

### 智能行为

```text
读哪个文件
搜索什么关键词
Bug 原因
如何修改
下一步 Tool
```

→ LLM

---

## 4. Tool vs Node

最常用判断：

```text
LLM 决定要不要调用
→ Tool

Graph 规定必须经过
→ Node
```

同一种能力可以因控制权变化而改变身份。

---

## 5. Node 怎么拆

不要按代码行数拆。

按“是否需要独立控制”拆。

强拆分信号：

- 中间需要路由；
- 独立 retry；
- 独立 interrupt；
- 不同权限；
- 独立观测 / 统计。

如果只是同一职责内部几步普通 Python 处理，不需要硬拆成多个 Node。

---

## 6. Capability Boundary vs Workflow Policy

### Capability Boundary

单次动作无论在哪调用都必须成立：

```text
read_file 不能越 workspace
run_test 单次 timeout
replace_text 不能模糊匹配
危险 shell 永远禁止
```

→ Tool / Code

### Workflow Policy

依赖整个任务历史：

```text
测试失败最多 3 次
最多修改 5 个不同文件
最多调用 shell 10 次
```

→ State + Graph

---

## 7. Completion Guard

原始 Agent：

```text
chat
↓
没有 tool_calls
↓
END
```

问题：

> 模型现在不想调用 Tool，不代表任务真的完成。

如果任务要求必须测试通过：

```text
无 tool_calls
↓
test_passed？
├─ True → final
└─ False → completion_guard → chat
```

核心：

> **LLM 可以提出结束意图，Graph 决定有没有结束资格。**

---

## 8. Completion Guard 也需要 Limit

否则：

```text
chat
↓
模型又想结束
↓
guard
↓
chat
↓
...
```

可以增加：

```python
premature_finish_count: int
```

达到上限：

```text
停止
→ final 报告未成功
```

注意：

> END / final 只表示流程停止，不自动等于成功。

---

## 9. Tool Call Guard

一个 AIMessage 可能一次提出多个 Tool。

无依赖：

```text
read a.py
read b.py
→ 可以同批
```

有依赖：

```text
replace_text
+
run_test
→ 不应该同批
```

可以设计：

```text
chat
↓
tool_call_guard
├─ 合法 → tools
└─ 冲突 → 不执行 → 给 LLM 反馈 → chat
```

核心：

> **LLM 提计划，Harness 校验计划。**

不要简单地把所有同批 Tool 强行本地串行，因为 Tool B 的参数可能需要 Tool A 的真实返回结果。

真正有数据依赖时：

```text
LLM
↓
Tool A
↓
结果
↓
LLM
↓
Tool B
```

更自然。

---

## 10. Approval 与 Hard Policy

例如“最多修改 5 个不同文件”。

当已经修改：

```text
a.py b.py c.py d.py e.py
```

如果 LLM 又想修改 f.py：

```text
Hard Policy
→ 直接拒绝
```

而不是：

```text
“要不要批准突破 5 个？”
```

除非需求明确写的是“默认 5 个，但用户可以覆盖”。

---

## 11. Harness 不是越厚越高级

一个成熟 Harness 的目标不是“把所有动作都写死”。

而是：

> **只把必须确定的东西确定下来，把剩下的自由交给模型。**

这是后面设计 Coding Agent V1 的核心判断标准。
