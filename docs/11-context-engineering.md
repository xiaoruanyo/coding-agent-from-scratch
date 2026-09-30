# 11. Context Engineering：让模型看到“正确的信息”，不是“所有信息”

Coding Agent 很容易遇到一个问题：

```text
search_code
↓
read_file 200 行
↓
read_file 200 行
↓
pytest 一大段日志
↓
继续搜索
↓
继续读取
...
```

messages 会越来越大。

Context Engineering（上下文工程）的目标不是“尽可能给模型更多”，而是：

> **在正确的时间，把正确的信息给模型。**

---

## 1. 为什么 Context 会膨胀

Agent Loop 不断产生：

```text
HumanMessage
AIMessage
ToolMessage
AIMessage
ToolMessage
...
```

Coding Agent 的 ToolMessage 还可能特别大：

- 大段代码；
- 搜索结果；
- pytest traceback；
- Repo 信息。

结果：

- token 成本上升；
- latency 增加；
- Context Window 逼近上限；
- 更严重的是旧信息和噪音会干扰模型。

所以：

> **Context 越大，不等于模型越聪明。**

---

## 2. 四层 Context 策略

推荐从轻到重：

```text
① 少拿
↓
② 少留
↓
③ 压缩
↓
④ 重要事实移出 messages
```

### 少拿

从源头控制：

```text
search_code 限制结果数
read_file 限制行数
pytest 输出限长
Repo 按需展开
```

最便宜的 token，就是从未进入 Context 的 token。

### 少留

已经过期的：

- 旧版本代码；
- 重复搜索结果；
- 不再需要的原始日志；

不应该永久反复发送给模型。

### 压缩

旧历史太长时：

```text
旧 messages
↓
Summary LLM
↓
Working Summary
```

### 重要事实移出 messages

例如：

```python
retry_count = 2
test_passed = False
```

应该由 State 可靠保存，而不是要求模型从几万 token 历史里重新推断。

---

## 3. Summary 的底层原理

语义 Summary 通常就是一次额外 LLM 调用：

```text
很长的旧历史
↓
总结模型
↓
较短的工作摘要
```

它会消耗一次调用，但可以让之后很多轮主模型少吃大量旧 Context。

Summary 不是无损压缩。

所以：

> 绝对不能丢的系统规则和精确程序事实，不能只依赖 Summary。

---

## 4. Working Summary 到底是什么

Working Summary：

> **当前任务的压缩工作现场 / 交接记录。**

它不是最终 Context。

推荐包含：

```text
1. 当前任务目标
2. 用户关键限制
3. 已确认事实
4. 已完成的重要动作
5. 当前未解决问题
6. 下一步仍然需要知道的信息
```

示例：

```text
【任务】
修复登录后 session 丢失。

【限制】
- 不修改 database.py
- 优先最小修改

【已确认】
- auth.py 是主要问题区域
- user.py 已排除

【已完成】
- 修改 auth.py 的 token 判空
- 已运行 pytest

【当前问题】
- 17 passed / 1 failed
- 剩余 session timeout

【下一步】
- 检查 session 创建与过期逻辑
```

不要写成流水账：

```text
先 search
然后 read
然后模型想了一下
然后又 read
...
```

---

## 5. Working Summary vs Memory

```text
Working Summary
→ 当前任务
→ task-scoped

Memory
→ 跨任务仍然值得复用
→ cross-task
```

例如：

```text
“auth.py 这次已经改了一次”
→ Working Summary

“这个项目统一使用 pytest”
→ Memory 候选
```

任务结束后，可以从 Summary 挑出真正长期有效的信息进入 Memory，但不要把整个任务摘要永久存储。

---

## 6. Working Summary 为什么可以放 State

Working Summary 不是“最终 Context”。

它是 Context Builder 的一个输入：

```text
旧 messages
↓
Summary LLM
↓
working_summary
       │
       ├── Recent Messages
       ├── System Prompt
       ├── Relevant Memory
       └── Latest Tool Result
              ↓
        Context Builder
              ↓
        最终 LLM Context
```

如果 working_summary 需要：

- 跨 Node 持续存在；
- Checkpoint；
- interrupt/resume 后继续使用；

那么放在 State 是很自然的。

但它和 `test_passed` 性质不同：

```text
working_summary
→ 给 LLM 理解任务现场

test_passed
→ 给 Graph 做硬判断
```

---

## 7. Context Builder

Context Builder 是一个架构职责，不一定非得是某个类。

它负责：

```text
Select
+ Compress
+ Order
```

也就是：

- 选哪些信息；
- 哪些要压缩；
- 按什么顺序给模型。

以后不要默认：

```python
model.invoke(state["messages"])
```

可以：

```python
context = build_context(state)
response = model_with_tools.invoke(context)
```

---

## 8. 一次 LLM Context 可能包含什么

概念上：

```text
System Prompt
+
Original Task
+
Selected State
+
Working Summary
+
Relevant Memory
+
Recent Messages
+
Latest Tool Result / Repo Context
```

不是每次都全部有。

### State 保存什么 != LLM 必须看到什么

例如：

```python
premature_finish_count = 1
```

Graph 可能需要，但主模型不一定需要知道。

---

## 9. Summary + Recent Messages

最常见策略：

```text
旧历史
→ Summary

最近几轮
→ 原样保留
```

为什么最近消息不立刻总结？

因为它们可能包含：

- 最新代码；
- 最新 traceback；
- 最新 Tool 返回；
- 刚刚的审批决定。

这些细节暂时仍然很重要。

---

## 10. 什么时候触发 Summary

不要每轮都总结。

概念：

```python
if context_too_large:
    summarize_old_history()
```

第一版不需要为了“高级”做复杂 Token Scheduler。

只要：

> Context 足够长时再压缩。

---

## 11. 过期上下文（Stale Context）

代码被修改后：

```text
磁盘
→ 新版本

历史 ToolMessage
→ 旧版本
```

模型可能同时看到两份内容。

重要理解：

> **LLM Context 是历史观测，不是真实世界本身。**

真实来源（Source of Truth）例如：

```text
文件内容
→ 当前磁盘

测试结果
→ 当前 pytest

审批
→ 实际用户输入

Graph 控制状态
→ Structured State
```

---

## 12. 修改后如何处理旧代码

V1 不需要复杂 hash/version 系统。

先用：

```text
Prompt 软提醒
+
replace_text 精确 old_text 匹配
+
真正需要继续分析时重新 read_file
```

例如：

```text
read auth.py
↓
replace_text auth.py
↓
run_test FAIL
↓
需要继续分析 auth.py
↓
重新 read_file 最新版本
```

Tool 的另一个重要价值因此出现了：

> **Tool 不只是帮 LLM 执行动作，也让 LLM重新观察真实环境。**

---

## 13. 是否要 dirty_files / hash

如果以后发现模型经常依赖旧版本，可以逐步加强：

```text
V0：Prompt

V1：Prompt + replace_text exact match

V2：dirty_files

V3：file hash / version + stale guard
```

不要第一版就把 Harness 做得很厚。

---

## 14. Coding Agent V1 推荐 Context 策略

最终收口：

```text
少读
+
局部读
+
旧历史 Working Summary
+
最近 Messages 原样保留
+
重要程序事实放 State
+
易变资源需要时重新读取
```

第一版 Context Builder：

```text
System Prompt
+
Working Summary
+
Recent Messages
```

后面再逐步加入：

```text
Relevant Memory
Selected State
Repo Context
```

核心：

> **不要试图让模型永远记住整个项目；让它记住任务进展，并在需要时重新观察代码。**
