# 08. 可靠执行：Retry、Loop、Recovery、Stream、Runner

Coding Agent 不是“能调用 Tool”就结束了。

真正运行起来后，会遇到：

- LLM API 临时错误；
- pytest FAIL；
- pytest timeout；
- interrupt 后等待用户；
- 多轮修复；
- 任务最终如何结束。

这一章解决的是 Runtime 可靠性。

---

## 1. 三种失败一定要分开

### Retry

```text
同一个动作原样再试
可能成功
```

例如：

```text
LLM API 临时连接错误
```

### Graph Loop

```text
动作正常执行
但业务结果不满意
```

例如：

```text
pytest 正常运行
↓
测试 FAIL
↓
重新分析 / 修改 / 测试
```

### Recovery

```text
原来的处理策略本身不值得继续重复
→ 换一种方法
```

例如：

```text
完整 pytest 一直 timeout
↓
不应该只重复完整 pytest
↓
改为定位卡住的测试 / 跑具体测试 / 查进程
```

一句话：

> **Retry = 再做一次；Loop = 重新解决；Recovery = 换一种解决方式。**

---

## 2. RetryPolicy

```python
from langgraph.types import RetryPolicy
```

概念：

```python
builder.add_node(
    "chat",
    chat_node,
    retry_policy=RetryPolicy(
        max_attempts=3,
    ),
)
```

适合：

- 没有不可逆副作用；
- 确实可能是临时异常；
- 原样重试有意义。

不要随便给整个 ToolNode 重试，因为 ToolNode 里可能有写文件等副作用。

---

## 3. try/except 与 RetryPolicy

如果：

```python
try:
    ...
except Exception:
    return {"error": "..."}
```

异常已经被吃掉，Runtime 看不到 Exception。

于是 RetryPolicy 不会触发。

如果需要交给 Runtime：

```python
except ConnectionError:
    raise
```

---

## 4. pytest FAIL 与 timeout

推荐把 run_test 结果结构化：

```python
{
    "passed": False,
    "output": "...",
    "error_type": ""
}
```

普通 FAIL：

```text
passed=False
error_type=""
→ retry_count + 1
→ Graph Loop
```

timeout：

```text
passed=False
error_type="timeout"
→ 不计入普通测试失败次数
→ final 或 Recovery
```

当还没有真正的 recovery Tool 时，直接结束并报告比造一个“空壳 recovery_node”更诚实。

---

## 5. Stream

`invoke()`：

```text
输入
↓
跑完整个 Graph
↓
最终结果
```

`stream()`：

```text
输入
↓
边运行
↓
边看到中间事件
```

常用：

```text
updates
→ 每个 Node 的更新

values
→ 每步后的完整 State

messages
→ LLM 消息 / token 流

tasks
→ task start / finish / error

debug
→ 详细调试信息
```

---

## 6. Runner

Runner 不属于 Graph 内部业务逻辑。

它是 Graph 外层应用代码。

职责：

```text
启动 Graph
↓
消费 stream
↓
发现 interrupt
↓
展示审批请求
↓
收集用户输入
↓
Command(resume=...)
↓
相同 thread_id 继续
```

典型：

```python
def run_until_pause_or_finish(graph_input, config):
    for chunk in app.stream(
        graph_input,
        config=config,
        stream_mode="updates",
    ):
        if "__interrupt__" in chunk:
            return "interrupted"

    return "finished"
```

外层循环：

```text
Graph 运行
↓
interrupted？
├─ 是 → 用户回答 → resume
└─ 否 → finished
```

---

## 7. 三种 Loop 不要混

```text
Graph Loop
→ 业务修复 / 重新测试

RetryPolicy
→ Runtime 层临时异常自动重试

Runner Loop
→ 外部持续处理 interrupt / resume
```

Runner 不负责：

- 决定测试失败还能否继续；
- timeout 应该怎么 Recovery；
- 判断任务是否成功；
- 校验 Tool 依赖关系。

这些属于 Graph / Harness。

---

## 8. final_report 与 END

```text
END
→ 程序停止执行

final_report
→ 给用户生成正式交付结果
```

所以可以：

```text
满足终止条件
↓
final_report_node
↓
END
```

final_report 使用普通 model，而不是 model_with_tools，可以避免最终汇报阶段再次调用 Tool。

---

## 9. 核心

```text
执行异常
→ Retry

业务失败
→ Graph Loop

策略失效
→ Recovery

暂停 / 恢复
→ Runner

正式交付
→ final_report
```
