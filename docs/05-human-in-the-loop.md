# 05. Human-in-the-loop：让高风险操作先问人

## 1. 为什么 Agent 不能什么都直接执行

读取文件通常低风险。

但：

```text
覆盖文件
删除文件
git reset --hard
生产环境操作
```

不能因为 LLM “觉得应该做”就直接执行。

因此需要 Human-in-the-loop（人工介入）。

## 2. interrupt

核心 API：

```python
from langgraph.types import interrupt, Command
```

例如：

```python
approved = interrupt({
    "action": "write_file",
    "path": path,
    "content": content,
    "question": "是否批准这次修改？",
})
```

执行到这里时：

```text
Graph 保存现场
↓
暂停
↓
外部应用显示审批信息
```

## 3. resume

用户做出决定后：

```python
Command(resume=True)
```

或者：

```python
Command(resume=False)
```

并且必须继续使用相同 `thread_id`。

## 4. 最重要的副作用规则

恢复时相关 Node / Tool 可能重新从前面执行。

因此：

> **不可重复副作用不要放在 interrupt() 前面。**

错误：

```text
先写文件
↓
interrupt
↓
问用户是否批准
```

正确：

```text
准备修改信息
↓
interrupt
↓
用户批准
↓
真正写文件
```

## 5. 只拦高风险 Tool

不需要每个 Tool 都审批。

推荐：

```text
read_file
search_code
list_files
→ 直接执行

write_file
replace_text
危险 shell
→ 执行前审批
```

## 6. Tool 内审批 vs 单独审批 Node

如果风险与 Tool 本身强绑定，可以把 interrupt 放在 Tool 内：

```text
replace_text
→ 准备修改
→ interrupt
→ 真正写入
```

如果审批本身需要复杂路由、批量 Diff、不同权限，则可能值得拆成单独流程。

## 7. Approval 不等于 Policy

一定区分：

```text
“需要用户确认”
→ Approval

“默认禁止，但允许用户覆盖”
→ Override Policy

“最多修改 5 个不同文件”
→ Hard Policy
```

如果需求说“最多 5 个”，第 6 个应该被系统拒绝，不应该默认问用户“要不要突破”。

## 8. 逐次审批与批量审批

逐次：

```text
每次 replace_text
→ interrupt
```

简单、安全，但多文件任务可能频繁打断。

批量：

```text
准备多个明确 Diff
↓
一次展示
↓
用户批准这一批具体修改
↓
只能执行已批准内容
```

批量审批不等于“从此整个工作区无限写权限”。

## 9. Runner 的角色

Graph 负责产生 interrupt。

Runner / UI 负责：

```text
展示
收集 y/n
Command(resume=...)
保持 thread_id
继续执行
```

这部分会在第 08 章进一步展开。
