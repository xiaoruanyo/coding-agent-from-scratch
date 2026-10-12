# N14｜让 Agent 读写真实仓库：Workspace、搜索、局部读取、精确修改

> **产品关联**：前端最终能看到代码搜索、文件片段和具体 Diff，但这些能力必须建立在实际受控的文件操作之上。学会调用 `read_file` 不等于已经获得安全的代码检索系统。

## 一、先看一个只写了两行的 Tool

```python
@tool
def read_file(path: str) -> str:
    return open(path, encoding="utf-8").read()
```

它能运行，却有五类明显的问题：

1. `../../secrets.txt` 或绝对路径可能让模型读到工作区之外。
2. 符号链接可能绕过字符串前缀检查。
3. 巨大文件会导致上下文膨胀，甚至读到二进制文件。
4. 读取到密钥后又交给外部 LLM，形成信息泄露风险。
5. 文件可能在模型分析之后、写入之前被其他进程修改。

因此不应该从“模型是可信的”出发，而要从“Tool 输入需要验证”出发设计。

## 二、明确授权范围：Workspace

我们只允许访问用户明确指定的项目目录：

```python
from pathlib import Path

workspace = Path("D:/projects/demo-project").resolve()
```

一段**教学用**路径解析代码：

```python
def resolve_path(relative: str) -> Path:
    requested = Path(relative)
    if requested.is_absolute():
        raise ValueError("不允许绝对路径")

    candidate = (workspace / requested).resolve()
    if not candidate.is_relative_to(workspace):
        raise ValueError("文件路径越过工作区")

    return candidate
```

注意：这处理了常见的 `..` 与现有符号链接越界问题，但不是防御并发路径替换的完整操作系统级沙箱。正式写入还要考虑“检查路径”与“打开文件”之间目标变化等 TOCTOU 风险。对不可信代码应配合操作系统隔离。

## 三、为什么要分开 search 和 read？

假设用户只说“金额计算错误”，我们不知道对应哪个文件。

低成本探索：

```text
list_directory → 了解目录结构
search_code("calculate_total") → 得到函数名与匹配文件
read_file("src/calculator.py", start_line=40, end_line=80)
                             → 看真正相关的代码
```

这里：

- `search_code` 负责**广而浅地定位**，返回文件名、行号、少量上下文，必须限制最大命中数；
- `read_file` 负责**窄而深地理解**，必须限制读取行数和字节数；
- `list_symbols` 可通过 Python AST 列出函数、类等结构，帮助找到真正的入口。

这比“把所有 Python 文件一次性发给模型”更适合大型项目。

## 四、读文件工具应该返回什么？

不要只返回一个没有上下文的巨大字符串。推荐提供：

```text
path: src/calculator.py
range: 40-80
total_lines: 137
truncated: false
content:
  40 | def calculate_total(items):
  41 |     ...
```

文件行号有助于模型定位，也有助于 UI 展示。`truncated` 字段告诉使用者结果经过截断，避免误以为看到了完整文件。

敏感文件排除列表不能只靠文件名。例如 `.env`、私钥、凭据文件应该默认拒绝或警告；但企业级秘密识别和外传治理仍是单独的高级主题。

## 五、写入已有文件为什么优先用 replace_text？

如果模型没有读取完整文件，却提交整文件覆盖：

```python
write_file("src/calculator.py", new_full_content)
```

可能删除与目标 Bug 无关的逻辑。

所以 V1 优先支持：

```python
replace_text(
    path="src/calculator.py",
    old_text="return a - b",
    new_text="return a + b",
)
```

但是必须对 `old_text` 做唯一匹配：

| 次数 | 行为 |
|---|---|
| 0 | 拒绝；旧上下文可能过期 |
| 1 | 允许进入审批和最终写入检查 |
| 2 或更多 | 拒绝；不能随便选择其中一处 |

这是一种非常有价值的保护：**模型的记忆可能过期，工具以当前文件事实为依据**。

## 六、写入一定分成“提案”和“执行”

```text
LLM 给出 replace_text 请求
      ↓
准备本次具体 Diff
      ↓
approval_gate / interrupt
      ↓
用户看到路径、旧文本、新文本
      ↓
批准 / 拒绝
      ↓
批准后再次校验文件与提案是否一致
      ↓
真正写入
      ↓
返回成功 / 失败 / 未执行
```

批准的是本次**具体的路径和内容**。不能显示 `main.py` 的一行 Diff，实际上执行另一条 `config.py` 修改。

文件成功修改还应使原先的测试通过状态失效。否则会出现“新文件从未测过，但旧的 PASS 仍被当成当前成功”。

## 七、为什么测试工具不能提供任意 Shell？

学习阶段应从固定命令开始：

```python
import subprocess
import sys

completed = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=workspace,
    capture_output=True,
    text=True,
    timeout=30,
)
```

这样减少了模型直接提供任意 Shell 命令的风险，也让测试结果和错误分类更明确。

**但运行 pytest 就是在执行测试模块的 Python 代码。** `cwd`、`timeout` 和不用 `shell=True` 都不能证明它是安全沙箱。V1 只用于自己信任的本地工作区；对不可信仓库必须有真实 OS 隔离与资源控制。

## 八、一次性写工具仍要处理的真实错误

- `old_text` 匹配不到：拒绝写入，并把错误交给模型重新读取。
- 文件有两个匹配位置：拒绝猜测。
- 当前路径经过符号链接指向工作区外：拒绝。
- 文件太大：拒绝或采用严格受限操作。
- 文件读取时编码错误：记录真实异常。
- 写入过程中异常：不能仅凭“抛错”就推断没有部分副作用。
- 文件审批期间被外部修改：拒绝过期审批，重新构造 Diff。

最终产品应为这些情况提供单元测试，而不是只放在文档警告里。

## 九、与产品 UI 的关系

用户在浏览器看到的不是“漂亮的模拟日志”，而应当是：

- 真实 `search_code` 的命中；
- 真实 `read_file` 的范围和内容摘要；
- 真实的审批提案；
- 真实的 `replace_text` 成功/失败；
- 真实的 pytest 结果。

只有这样，前端才是 Coding Agent 的操作界面，而不只是聊天皮肤。

**理解检查**：为什么“每个 Tool 都在它自己的实现里验证 workspace”通常比只在 System Prompt 写“只能在项目内操作”更可靠？为什么精确匹配失败后应该重新读取，而不是让模型猜测行号？
