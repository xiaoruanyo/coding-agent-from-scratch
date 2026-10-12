# N01｜先把实验环境搭稳：Windows、PyCharm、Python、模型 API

> 本课目标：在你自己的 Python 解释器里完成依赖安装，确认环境变量可读，并把“环境错误”和“Agent 逻辑错误”分开。

## 1. 为什么环境这一步值得单独讲？

很多初学者不是卡在 `StateGraph`，而是卡在：

- 电脑里有多个 Python 版本；
- 命令行安装在一个解释器，PyCharm 运行在另一个解释器；
- PowerShell 设置了临时环境变量，但 PyCharm 没继承；
- `pip install` 看似成功，运行仍然 `ModuleNotFoundError`；
- API 密钥明明有，却读到 `KeyError`；
- 模型名和服务商当前支持的名称不一致。

这些问题如果不先区分，很容易误以为 LangGraph 本身有问题。

这套教程的早期实践主要使用 **Windows + PyCharm + Python 3.13**。如果你已经有一个能正常工作的解释器，不需要为了教程重装 Python。

## 2. 创建一个独立虚拟环境

在 PyCharm 打开课程项目。你可以使用 PyCharm 的图形界面配置 Project Interpreter，也可以在项目目录的终端中执行：

```powershell
py -3.13 -m venv .venv
```

如果本机没有 `py -3.13`，也可以用当前正确的 Python：

```powershell
python -m venv .venv
```

Windows PowerShell 激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

如果因为 PowerShell 执行策略无法激活，不需要为了继续安装而修改全局安全策略。直接运行虚拟环境中的解释器也可以：

```powershell
.\.venv\Scripts\python.exe -m pip --version
```

关键是**用哪个 Python 运行，就用哪个 Python 安装依赖**：

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "langgraph==1.2.11" langchain-openai python-dotenv pytest
```

`langgraph==1.2.11` 是本课程历史学习环境使用过的版本；`langchain-openai` 及其他未锁定依赖可能会随时间变化。在可复现的正式项目里，后面还应锁定完整依赖版本。

## 3. 不要凭感觉判断当前解释器

创建 `check_env.py`：

```python
import sys
import importlib.metadata

print("Python 可执行文件:", sys.executable)
print("Python 版本:", sys.version)

for package in ("langgraph", "langchain-openai", "langchain-core"):
    try:
        print(package, importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:
        print(package, "没有安装")
```

用 PyCharm 运行它，观察实际路径。例如：

```text
Python 可执行文件: D:\project\.venv\Scripts\python.exe
langgraph 1.2.11
...
```

**上面只是输出示例，不是保证你的机器显示相同路径或版本。**

如果 `sys.executable` 指向系统 Python，而你把包装进了 `.venv`，应调整 PyCharm Interpreter。不要无目的地反复卸载重装。

## 4. 理解 API Key 为什么读不到

模型服务一般需要 API Key。为了避免密钥泄露，**不要把真实 Key 写入 Git 仓库、教材示例、日志或报错截图**。

初学者常写：

```python
import os

api_key = os.environ["DEEPSEEK_API_KEY"]
```

如果当前 Python 进程没有这个环境变量，`os.environ[...]` 会直接抛出 `KeyError`。

这不代表密钥一定无效，甚至还没走到网络请求。报错发生在 Python 读取环境变量的阶段。

可以先检查**变量是否存在**，不要打印密钥值：

```python
import os

print("API Key 已配置？", bool(os.getenv("DEEPSEEK_API_KEY")))
```

PowerShell **仅当前终端会话**的临时设置示例：

```powershell
$env:DEEPSEEK_API_KEY = "填入你自己的真实密钥"
```

但要注意：如果 PyCharm 是从别的进程启动的，它不一定继承这个终端的临时变量。更稳妥的办法是给 PyCharm Run Configuration 配置环境变量，或使用一个只保存在本机、被 `.gitignore` 排除的 `.env` 文件。

## 5. 使用本机 .env，避免把 Key 提交到仓库

本地的 `.env` 例子：

```dotenv
DEEPSEEK_API_KEY=填入你自己的真实密钥
DEEPSEEK_MODEL=你当前账号实际可用的模型名
```

将下面规则加入仓库的 `.gitignore`：

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
```

注意：`.gitignore` 只阻止尚未被 Git 跟踪的文件被新增。如果你以前已经把密钥提交过，需要按密钥泄露处理，撤销该密钥并重新签发；仅新增 ignore 不会从历史中抹掉它。

通过 `python-dotenv` 在本地加载：

```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
model_name = os.getenv("DEEPSEEK_MODEL")

if not api_key:
    raise RuntimeError("没有读取到 DEEPSEEK_API_KEY；请检查 .env 或 IDE 运行配置")

if not model_name:
    raise RuntimeError("没有读取到 DEEPSEEK_MODEL；请填写服务商当前可用的模型名")
```

此时我们只是检查配置，还没有调用模型。

## 6. 区分三种失败

### A. Python 环境错误

```text
ModuleNotFoundError: No module named 'langgraph'
```

排查解释器、`python -m pip` 和虚拟环境。

### B. 配置错误

```text
KeyError: 'DEEPSEEK_API_KEY'
```

排查当前进程的环境变量，不要先怀疑 LLM 逻辑。

### C. API 调用错误

例如认证失败、模型名不支持、余额限制、请求频率限制、网络超时等。这类错误说明代码已经尝试与外部服务交互。要结合真实响应诊断。

三者处理方式不同。如果你把所有异常都写成：

```python
try:
    ...
except Exception:
    print("模型出错，重试")
```

就会掩盖真正原因，而且配置错误、鉴权错误未必能通过盲目重试解决。

## 7. 一个简洁的排查顺序

```text
项目运行失败
  │
  ├─ 找不到包？
  │    └─ 检查 sys.executable + 依赖安装位置
  │
  ├─ 读不到 Key？
  │    └─ 检查当前 Python 进程的环境变量
  │
  ├─ API 返回错误？
  │    └─ 检查服务商地址、模型名称、配额和网络
  │
  └─ API 通了，但行为不对？
       └─ 才开始分析 Prompt、Messages、Tool 或 Graph
```

## 8. 常见误解

**误解：我在 PowerShell 里能读取到变量，PyCharm 就一定能读取。**

不一定。环境变量属于进程继承关系，要检查实际启动 Python 的那个进程。

**误解：Python 3.13 可以用，就表示所有依赖都与它兼容。**

不能这样推断。应以具体安装版本与实际运行测试为准。

**误解：课程曾经使用过某个 DeepSeek 模型名，所以以后都能照搬。**

模型名称可能因服务端变化而改变。教程把模型名放到 `DEEPSEEK_MODEL`，避免把服务商的时点配置混同为 LangGraph 的核心知识。

**误解：为了调试方便，把完整 API Key 打印出来。**

没有必要。打印“是否配置”就够了。

## 9. 理解检查与本课验收

你应能做到：

- 在 PyCharm 里准确说出 `sys.executable` 指向哪个 Python。
- 解释 `python -m pip` 比不带解释器路径的 `pip` 更容易避免什么问题。
- 不显示真实 Key，只判断当前进程能否读取密钥。
- 遇到 `KeyError` 时不把问题归咎于 LangGraph 的 State。
- 明白 `.env` 是本机配置而非应该提交的教材素材。

下一课：[N02｜第一次调用聊天模型](N02-first-model.md)。
