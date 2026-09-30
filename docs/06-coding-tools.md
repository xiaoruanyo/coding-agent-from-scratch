# 06. Coding Agent 工具链：让模型真正理解和修改代码

## 1. Workspace 安全边界

第一原则：

> Agent 只能操作指定 workspace。

课程中的基本做法：

```python
WORKSPACE = (BASE_DIR / "sandbox").resolve()
```

任何用户 / LLM 提供的路径：

```text
输入 path
↓
resolve()
↓
检查 is_relative_to(WORKSPACE)
↓
只允许 workspace 内路径
```

这是 Tool 自己的 Capability Boundary（能力边界）。

## 2. list_files / list_directory

用途：

> 让模型先知道项目大概有什么。

不一定一上来读取所有代码。

## 3. search_code

职责：

```text
广、浅
→ 用关键词快速定位可能相关的位置
```

例如：

```text
search_code("refresh_token")
```

返回命中位置附近少量上下文。

应有结果数上限，例如：

```text
MAX_SEARCH_RESULTS
```

## 4. bounded read

read_file 不应该随便返回几千行。

例如：

```python
read_file(
    path="auth.py",
    start_line=120,
    end_line=220,
)
```

同时 Tool 内有：

```text
MAX_READ_LINES
```

所以即使模型一次要求 3000 行，也会被资源边界限制。

推荐代码探索：

```text
search_code
→ 广、浅

read_file
→ 窄、深
```

## 5. write_file 与 replace_text

### write_file

适合：

- 新建文件；
- 确实需要整文件写入。

### replace_text

适合：

- 修改已有文件的一小部分。

```python
replace_text(
    path,
    old_text,
    new_text,
)
```

安全策略：

```text
old_text 匹配 0 次
→ 拒绝

匹配 1 次
→ 可以修改

匹配 >1 次
→ 拒绝猜测
→ 让模型重新 search / read 获取更精确上下文
```

这同时提供了一层“旧上下文保护”：

如果模型拿着过期代码调用 replace_text，old_text 很可能已经匹配不到，于是不会盲目写坏文件。

## 6. run_test

课程使用：

```python
[
    sys.executable,
    "-m",
    "pytest",
]
```

并设置：

```text
timeout=30
```

要区分：

```text
pytest 正常运行但 FAIL
→ 业务失败

pytest timeout / 环境异常
→ 执行异常
```

推荐结构化结果：

```python
{
    "passed": False,
    "output": "...",
    "error_type": "timeout",
}
```

不要只依赖自然语言字符串。

## 7. Tool Error Handling

大致分三类：

### 可预期业务失败

Tool 正常返回：

```text
测试不通过
文件不存在
old_text 找不到
```

让 LLM / Graph 继续处理。

### 可预期执行异常

例如：

```text
timeout
UnicodeDecodeError
OSError
```

可以转成结构化错误。

### 程序自身 Bug

不要用一个巨大的：

```python
except Exception:
    return "失败"
```

把所有编程错误都吞掉。

否则 Runtime / RetryPolicy 也无法知道真正发生了异常。

## 8. Tool vs Node

```text
LLM 决定要不要调用
→ Tool

Graph 规定必须经过
→ Node
```

例如当前架构里：

```text
run_test 何时执行由 LLM 决定
→ Tool
```

如果以后规定：

```text
每次修改后 Graph 强制测试
```

那它可以被设计成 Node。

## 9. 核心

> 搜索用来缩小范围，读取用来获取细节，修改优先最小改动，所有 Tool 自己守住单次动作的硬边界。
