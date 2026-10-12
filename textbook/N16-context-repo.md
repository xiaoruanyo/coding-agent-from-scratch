# N16｜Context Engineering：让模型看到正确的代码，而不是整个仓库

> 这课连接两条主线：一条是模型请求上下文会不断增大；另一条是 Coding Agent 必须在越来越大的 Repo 中找到真正相关的代码。

## 一、为什么把仓库全部喂给模型不是好办法？

假设用户只要求修复 `calculate_total`，仓库却有 10 万行代码。

如果我们直接把所有文件拼接进 Prompt：

- 大量无关信息消耗 token；
- 重要代码会被噪音淹没；
- 文件在 Agent 运行期间可能发生修改，旧内容变得不可信；
- 历史 ToolMessages 会不断重复进入模型请求；
- 成本和响应时间都不可预测。

因此 Context Engineering（上下文工程）不是“压缩 Prompt 小技巧”，而是**在正确的时间，把正确的数据交给模型**的系统设计。

## 二、区分三个数据集合

### 1. Graph State

Graph 真正要跨节点保存的程序事实，例如：

```python
retry_count = 2
test_passed = False
last_error_type = "TEST_FAIL"
```

这些信息用于确定性路由，不能只依赖模型从聊天记录猜。

### 2. 完整事件与历史

当前任务确实发生过的工具调用、审批、文件修改和测试结果。Checkpoint 或外部事件存储可能保留它们，便于恢复与审计。

### 3. 本轮给模型的 Context

当前 LLM 请求真正读取的消息集合：

```text
System Prompt（稳定规则）
+ Working Summary（压缩后的工作进度）
+ Recent Messages（最近重要消息）
+ Relevant Repo Context（当前相关的代码）
+ Selected Facts（当前可核验状态）
```

前两者可能很大，但第三者应当有所选择。**存储历史不是让模型每轮看完全部历史。**

## 三、从源头减少上下文

与其等到几万 token 再摘要，不如先限制工具输出：

- `list_directory` 控制最大深度与返回条数；
- `search_code` 限制命中数与周边上下文；
- `read_file` 控制最大行数；
- pytest 输出只保留重要摘要与有限尾部日志；
- Repo Map 先提供函数/类结构，需要时再读取实现。

最便宜的 token 是没有进入 Context 的 token。

## 四、代码检索应该从粗到细

```text
目录树与 Repo Map
     ↓
找到候选文件
     ↓
关键字搜索/符号定位
     ↓
读取真实源代码的局部范围
     ↓
分析、修复、验证
```

### 关键词搜索适用于已知名字

例如错误指出 `calculate_total`，搜索这个名字通常非常有效、便宜，也不需要先建立向量数据库。

### Repo Map 适用于不知道入口在哪

Python 可以通过标准库 `ast` 提取类、函数、方法定义：

```python
import ast
from pathlib import Path

source = Path("calculator.py").read_text(encoding="utf-8")
tree = ast.parse(source)

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        print(node.name, node.lineno)
```

这段代码得到的是可从源代码确定的符号信息，而不是让 LLM 猜“这个仓库有哪些函数”。

### RAG 并非第一天就必须加入

如果用户只知道语义：“登录后状态丢失”，但不知道代码里叫 `create_session`，语义检索可能很有帮助。

但 RAG 召回的是“可能相关”，不能代替再次读取真实文件核实结论。第一版先掌握目录、AST 和关键词搜索，已经能够解决大量局部修复场景。

## 五、Working Summary 是什么？

Coding Agent 经过十几次工具调用后，完整 Messages 可能有数千行 pytest 输出和大量过期代码。

Working Summary 是**当前任务的紧凑工作交接记录**：

```text
任务：修复 calculate_total 对折扣处理的错误。
已经确认：tests/test_total.py 断言不通过。
相关位置：src/calculator.py:40-60。
曾尝试：替换旧表达式，被用户拒绝，文件未修改。
当前事实：retry_count=1，test_passed=False。
下一步：重新分析允许的替代方案。
```

它可以让模型记住工作方向，却不是不可变事实的唯一来源。

例如“文件已修改”应来自真实写入结果；“测试已通过”应来自可靠的测试记录；“用户批准”应来自审批层。

## 六、Summary 的两个误区

**误区 A：摘要是无损压缩。**

不是。摘要会丢失细节，可能忽略某次工具的关键结果。不能让它承担精确授权、失败次数等系统规则。

**误区 B：有 Summary 就不再读取磁盘。**

恰好相反。对于容易变化的文件内容，摘要只记录曾经看到什么；真正准备修改前，需要重新观察工作区并核验旧内容。

## 七、Context 过期是 Coding Agent 特有的常见问题

时间线：

```text
10:00 读取 main.py 第 50 行
10:02 另一个进程修改 main.py
10:05 模型用旧代码生成 replace_text
```

如果工具盲目信任模型，可能覆盖别人的新修改。

因此应当：

1. 模型使用搜索/摘要定位目标；
2. 在真正修改前读取或核验当前版本；
3. 工具要求 `old_text` 唯一匹配，必要时比较文件哈希；
4. 失败时重新搜索和读取，**不能默默改成模糊替换**。

“Context 相关”与“Context 最新”是两个独立要求。

## 八、Context Builder 应该作为独立 Node 吗？

不一定。

如果构造上下文只是 `chat_node` 中的一段确定性 Python 逻辑，可以先把它作为普通函数：

```python
def build_context(system, summary, recent_messages, repo_context):
    # 示意：真实实现还要处理 Token 预算与消息配对协议。
    return [system, summary, *recent_messages, repo_context]
```

这是**架构片段**，不是完整可运行的 LangChain Messages 代码，因为 `summary`、`repo_context` 还需转换成合适的消息对象，历史工具调用与 ToolMessage 的对应关系也不能被破坏。

什么时候拆独立 Node？例如需要独立压缩、状态写入、观测、错误恢复时。

## 九、与最终产品对应

- 用户看到的检索时间线来自真实 `list_directory / search_code / read_file`；
- 模型侧 Context Builder 只提供必要代码；
- 旧摘要帮 Agent 保持任务进度；
- UI 的任务历史由 Task Store 提供，不必全部进入模型；
- 修改前的版本核验避免过期 Context 引起静默覆盖。

## 十、理解检查

1. 为什么 Checkpoint 保存了所有消息，不等于下一轮应该把全部消息传给模型？
2. 关键词搜索、Repo Map、RAG 各解决什么不同的问题？
3. 为什么 Working Summary 不适合单独保存审批授权结果？
4. 模型记住的函数实现与磁盘上的当前实现不一致时，谁应该被相信？

**关键原则：不要试图让模型永远记住整个 Repo，而要让它随时找到当前真正需要的、最新的代码。**
