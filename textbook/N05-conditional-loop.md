# N05｜Conditional Edge 和 Loop：亲手完成“检查—重写—再检查”

> 本课目标：解决一个真实的控制问题——检查不合格时重复处理，合格时退出。这个练习也是 Coding Agent “测试失败→修复→再测试”循环的最小原型。

## 1. 先理解普通 Edge 为什么不够

上一课：

```text
create → writer → END
```

不需要判断，固定前进即可。

现在要求：

> 检查文章质量，评分达到 80 才结束；没达到 80 则重写，然后重新检查。

```text
                 ┌───────────────┐
                 │               │
                 ▼               │
              check ── 不合格 → rewrite
                 │
               合格
                 ▼
                END
```

这里 `check` 做的是“计算检查结果”，但**下一步去哪**属于流程路由职责。

于是有了 Conditional Edge（条件边）。

## 2. State：要保存哪些东西？

先定义：

```python
from typing import TypedDict

class ArticleState(TypedDict):
    article: str
    score: int
    check_count: int
```

为什么有 `check_count`？

因为示例要区分第一次检查与之后的检查。更重要的是，我们希望演示“同一个字段被多轮 Node 可靠更新”，而不是让程序从打印日志中数执行次数。

## 3. 检查节点：只负责更新事实

为了让示例离线运行、不依赖模型，我们先用确定性规则模拟评分：

```python
def check_article(state: ArticleState):
    count = state["check_count"] + 1

    if count == 1:
        score = 70
    else:
        score = 90

    print(f"第 {count} 次检查，分数 = {score}")
    return {
        "check_count": count,
        "score": score,
    }
```

这段代码**没有真正评估文章内容**。它只是教学用的模拟器，故意第一次给 70、第二次给 90，好让我们观察循环。正式业务里必须换成有真实依据的检查过程。

### 一个容易忽略的细节

`count = state["check_count"] + 1` 读取的是进入当前 Node 时的值。

`return {"check_count": count}` 才把新的计数交给 Runtime 合并。

如果最初没有提供 `check_count`，第一步就可能遇到 `KeyError`。

## 4. 重写节点：只负责更新文章

```python
def rewrite_article(state: ArticleState):
    print("执行重写")
    return {
        "article": "这是重写后的文章"
    }
```

为什么这里不直接写 `score=90`？

因为 `score` 是**检查结果**，而不是重写动作理应拥有的事实。

重写后到底有没有达到 90，应当由下一次 `check_article` 产生结果。这个边界与 Coding Agent 的“修改文件不等于测试通过”完全一致。

## 5. Router：读 State 并决定走向

```python
def route_article(state: ArticleState):
    if state["score"] >= 80:
        return "pass"
    return "rewrite"
```

这段函数不写文章，不评分，只做一件事：

> 根据已保存的状态，给出路由标签。

可以用中文解释成：

```text
score >= 80 → pass
否则        → rewrite
```

`pass` 和 `rewrite` 只是我们自己定义的路由标签，不是 LangGraph 自动发明的魔法词。

## 6. 完整可运行代码

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class ArticleState(TypedDict):
    article: str
    score: int
    check_count: int

def check_article(state: ArticleState):
    count = state["check_count"] + 1
    score = 70 if count == 1 else 90
    print(f"第 {count} 次检查，评分：{score}")
    return {"check_count": count, "score": score}

def rewrite_article(state: ArticleState):
    print("重新写文章")
    return {"article": "这是重写后的文章"}

def route_article(state: ArticleState):
    if state["score"] >= 80:
        return "pass"
    return "rewrite"

builder = StateGraph(ArticleState)

builder.add_node("check", check_article)
builder.add_node("rewrite", rewrite_article)

builder.add_edge(START, "check")

builder.add_conditional_edges(
    "check",
    route_article,
    {
        "pass": END,
        "rewrite": "rewrite",
    },
)

builder.add_edge("rewrite", "check")

graph = builder.compile()

result = graph.invoke({
    "article": "原始文章",
    "score": 0,
    "check_count": 0,
})

print("最终 State:", result)
```

## 7. 不要跳过运行结果：我们逐步拆

初始：

```text
article = "原始文章"
score = 0
check_count = 0
```

**第一步，进入 check。**

```text
count = 0 + 1 = 1
score = 70
```

check 返回：

```python
{"check_count": 1, "score": 70}
```

State 更新后，route_article 读取到 `score=70`，返回 `"rewrite"`。

**第二步，进入 rewrite。**

```text
article = "这是重写后的文章"
```

然后因为存在：

```python
builder.add_edge("rewrite", "check")
```

流程回到 check。

**第三步，再次 check。**

```text
count = 1 + 1 = 2
score = 90
```

这次 `route_article` 返回 `"pass"`，映射到 `END`。

因此最终大致可见：

```python
{
    "article": "这是重写后的文章",
    "score": 90,
    "check_count": 2,
}
```

这是基于教学代码的确定性推演。你可以实际运行验证打印顺序。

## 8. 两个我们真的容易写错的地方

### 错误一：`route_article()` 和 `route_article`

错误：

```python
builder.add_conditional_edges("check", route_article(), ...)
```

正确：

```python
builder.add_conditional_edges("check", route_article, ...)
```

原因是 `add_conditional_edges` 需要的是一个“以后调用的路由函数”，而不是你现在立刻调用后的返回值。

而且当前 `route_article` 需要一个 `state` 参数；写 `route_article()` 甚至会因为缺少参数而直接抛异常。

### 错误二：忘了 `check_count` 初值

如果节点内执行：

```python
state["check_count"] + 1
```

却没有从输入或上游更新里得到 `check_count`，就会失败。

对我们的例子，最直观的做法是在 `invoke` 时提供 `check_count: 0`。

## 9. 第三个隐藏风险：无限循环

假设检查节点无论重写多少次都返回 70：

```python
def check_article(state):
    return {"score": 70}
```

Graph 就会一直尝试：

```text
check → rewrite → check → rewrite → …
```

这说明：

**有 Loop 还不够，可靠的 Agent 需要明确的终止机制。**

我们在本章用“第二次评分 90”让示例自然结束。在真正的 Coding Agent 里，要有更严格的规则，比如普通测试失败最多三次、超时单独处理、工具错误不能盲目当作业务失败。

不要把一次 Graph 的最大递归执行保护，错误地当成业务层明确的“最多重试三次”策略。业务规则应由明确计数和路由实现。

## 10. 把文章例子映射到 Coding Agent

| 文章示例 | Coding Agent 对应 |
|---|---|
| `rewrite_article` | 修改代码 |
| `check_article` | 运行测试 / 解析测试结果 |
| `score` | `test_passed` / 错误类型 |
| `check_count` | `retry_count` |
| `route_article` | 完成条件与失败分支 |
| `END` | 工作流真正停止 |

但请注意，文章示例的评分是模拟值；Coding Agent 的 `test_passed=True` 必须来自真实测试成功，不应该凭模型的描述来设置。

## 11. 为什么“条件”通常表现为 Edge？

这曾是一个学习中的好问题：“为什么把条件写在边上，而不是再造一个判断 Node？”

两种方式都能实现，但职责上可以这样看：

- 业务步骤产生信息，例如 `check` 计算 `score`。
- 路由函数读已有信息并选择下一步，不必产生新 State。
- 当判断本身需要独立副作用、审计或状态更新时，也可能值得做成 Node。

因此“条件边”不是说判断不存在 Python 函数，而是 Graph 把“做事”和“根据结果选路”区分开了。

## 12. 一道真正需要理解的题

如果你将 `rewrite_article` 改成：

```python
return {
    "article": "新版文章",
    "score": 90,
}
```

那么下一次 check 还没有运行时，State 里就先出现了“90”。

请想一想：

> 这会不会把“重写动作的预期”与“检查产生的事实”混为一谈？

这正是未来 Agent 设计里“意图不等于事实”的原型。

下一课：[N06｜Reducer](N06-reducer.md)。
