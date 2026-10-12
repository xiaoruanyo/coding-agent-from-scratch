# 教材随课代码

本目录与 `textbook/Nxx` 正文配套；它不是完整 Coding Agent 成品。

## 先运行不需要 API 的脚本

在仓库根目录或本目录配置好虚拟环境并安装：

```powershell
python -m pip install -r textbook/examples/requirements.txt
```

然后：

```powershell
python textbook/examples/01_first_graph.py
python textbook/examples/02_conditional_loop.py
python textbook/examples/03_reducer.py
python textbook/examples/06_sync_test_result.py
python -m pytest textbook/examples/test_sync_result.py -q
```

这些脚本不需要连接大模型；适合先确认 `StateGraph`、`Conditional Edge`、`Reducer` 与事实同步规则。

## 再运行需要 API 的脚本

复制 `.env.example` 内容到**项目工作目录**的本地 `.env` 并填写真实密钥、当前可用的模型名；请确认 `.env` 没有被 Git 跟踪。

```powershell
python textbook/examples/04_first_model.py
python textbook/examples/05_tool_loop.py
```

它们涉及真实 API 请求和可能的调用费用。模型输出和工具调用行为可能有差异，不应通过比较固定自然语言字符串来验收。

## 文件与课程对照

| 文件 | 对应教材 | 不可忽略的观察点 |
|---|---|---|
| `01_first_graph.py` | N04 | 节点返回局部更新，Graph 合并 State |
| `02_conditional_loop.py` | N05 | 70 → 重写 → 90，`check_count=2` |
| `03_reducer.py` | N06 | 两次局部 list 更新被合并 |
| `04_first_model.py` | N02 | 返回 AIMessage 而非字符串 |
| `05_tool_loop.py` | N07～N08 | Tool Calls 只是意图，ToolNode 才执行 |
| `06_sync_test_result.py` | N10 | PASS / FAIL / TIMEOUT / ERROR 分类 |
| `test_sync_result.py` | N10 | 普通 FAIL 才消耗失败次数预算 |

## 关于验证声明

- 可以对纯 Python 代码做语法检查和单元测试。
- LangGraph 相关脚本仍需要你安装课程依赖才能完整执行。
- 外部模型相关脚本必须使用实际可用的 API 账号与模型名验证。
- 教材里“预期输出”是便于理解的典型现象；具体 metadata 与回答内容不可视为固定快照。
