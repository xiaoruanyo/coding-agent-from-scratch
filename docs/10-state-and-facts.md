# 10. State 设计：意图不是事实，State 也不是日志

## 1. 一个关键错误：把 LLM 的计划当成系统事实

LLM 说：

```text
“我要修改 a.py”
```

只代表：

> 意图。

不代表：

```python
modified_files = ["a.py"]
```

因为：

- 用户可能拒绝审批；
- Tool 可能执行失败；
- old_text 可能匹配不到；
- 文件可能根本没被写入。

---

## 2. 正确链路

```text
LLM 表达意图
↓
Tool Call
↓
审批 / 执行
↓
Tool 产生真实结果
↓
ToolMessage
↓
sync_state
↓
State 保存事实
```

例如：

```text
LLM：“测试应该没问题”
≠ test_passed=True

run_test 真实通过
→ test_passed=True
```

核心：

> **LLM 负责表达意图，Tool 负责产生事实，State 负责保存事实，Graph 根据事实执行规则。**

---

## 3. Tool 返回结构化结果

如果程序需要消费 Tool 输出，优先：

```python
{
    "success": True,
    "action": "replace_text",
    "path": "a.py",
}
```

而不是依赖：

```python
"成功" in tool_message.content
```

自然语言适合给人 / LLM 看，结构化数据适合程序判断。

---

## 4. modified_files 怎么更新

如果限制：

> 整个任务最多修改 5 个不同文件。

那么：

```text
LLM 想修改 a.py
→ 不更新

用户批准 + Tool 真正写入成功
→ modified_files 加入 a.py
```

如果已经有 5 个文件：

```python
if path in modified_files:
    # 已经修改过，不增加“不同文件”数量
    allow
elif len(modified_files) < 5:
    allow
else:
    deny
```

---

## 5. State 不是 Agent 日志

不要看到什么都放进去：

```text
current_code
search_result
planned_fix
last_tool_output
reasoning
current_file
files_read
...
```

这样会产生：

- 重复；
- stale state（过期状态）；
- 同步困难；
- 字段语义越来越模糊。

---

## 6. 四问法

一个字段要不要进 State，先问：

```text
1. 后面的 Graph / Node 真的会结构化读取吗？
2. messages 里是不是已经足够？
3. 它跨多个步骤仍然有意义吗？
4. 它的语义是否明确、稳定？
```

---

## 7. current_file 为什么经常不值得放

“当前文件”到底是什么意思？

```text
最后读取的？
准备修改的？
刚修改的？
主要问题文件？
```

语义不稳定。

如果 Graph 并没有根据它：

- 路由；
- 计数；
- 强制逐文件执行；

那么 messages 已经能让 LLM知道当前关注了什么。

---

## 8. files_read 什么时候有价值

如果只是：

> LLM 想知道之前读过什么。

messages 足够。

如果规则是：

> 整个任务最多读取 20 个不同文件。

那么 Graph 必须计数，此时：

```python
files_read: list[str]
```

就有明确用途。

---

## 9. State 可以存“工作数据”，不只存路由字段

例如后面的：

```python
working_summary: str
```

它不一定被 Edge 判断，但需要：

- 跨 Node 保存；
- Checkpoint；
- 下一轮 Context Builder 读取。

所以也可以放 State。

区别只是：

```text
working_summary
→ 给 LLM 使用的任务工作数据

test_passed
→ 给 Graph 使用的系统事实
```

---

## 10. 强模型 + 薄 Harness 对 State 的影响

模型承担更多动态判断时：

```text
State
→ 可以更小
```

Graph 承担更多固定 Workflow 时：

```text
State
→ 往往需要更多控制字段
```

所以：

> State 设计不能脱离整体控制权分配单独讨论。

---

## 11. 本章核心

> **State 不是“可能有用的信息集合”，而是程序真正需要跨步骤持续保存的结构化数据。**

以及：

> **先区分意图和事实，再决定什么时候更新 State。**
