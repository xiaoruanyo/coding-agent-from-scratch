# N18｜第一条产品闭环：从浏览器点击“修复”到真实 pytest

> **这一课不是让你照着截图点三下按钮。** 我们要把之前分散学习的 HTTP、Tool、文件审批、测试结果和 UI 状态连成同一条可观察的数据流。这里先使用可复现的确定性演示驱动器，后面再让 LangGraph + LLM 替换其决策角色。

## 一、为什么先做一次确定性产品演示？

如果一上来就同时调试：

```text
DeepSeek API
LangChain bind_tools
LangGraph
Checkpoint
FastAPI
SSE
React
Diff
文件写入
pytest
```

当用户点击“开始任务”以后什么都不发生，你很难立即判断到底错在哪一层。

所以我们刻意先做一个固定例子：

**给定 calculator.py 的减法错误，生成提案、审批、真正修改、运行测试、从浏览器看见结果。**

它不是通用 Coding Agent 的能力展示，而是**产品通路验证**。可以把它理解为：先让电路通电、传感器有读数，再安装聪明的大脑。

## 二、先理解 M0 的文件结构

```text
product/
├── backend/
│   ├── app/core.py       # 文件边界、提案、真实写入、运行测试
│   ├── app/main.py       # 任务、审批、事件流 HTTP API
│   ├── tests/            # 只在临时目录运行的规则测试
│   └── requirements.txt
├── frontend/
│   ├── src/App.tsx       # 任务表单、时间线、审批、测试面板
│   ├── src/styles.css    # 界面
│   └── vite.config.ts    # 开发代理
└── sample-workspace/
    ├── calculator.py     # 故意写错的计算函数
    └── test_calculator.py
```

后端不需要完整复制项目进 Graph State；它只存必要的任务记录和待审批提案。

## 三、运行前先看测试用例

```python
# calculator.py
def calculate_total(a: int, b: int) -> int:
    return a - b

# test_calculator.py
def test_calculate_total():
    assert calculate_total(6, 4) == 10
```

这段代码有一个明确 Bug：`6-4=2`，但业务希望两个数字求和，结果应为 `10`。

为什么特意使用确定性错误？

因为我们想**独立验证产品是否真实执行修改和测试**，而不是把正确性押在 LLM 每次是否恰好推理到同一种修复上。

## 四、启动后端

在仓库根目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r product/backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn product.backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

另一种方式是先在 PyCharm 中选定项目 `.venv` Interpreter，再通过终端运行上述命令。

为什么使用 `127.0.0.1`？

当前产品只面向本机可信练习目录，不需要将开发 API 暴露给局域网。注意：本地监听并非足够的生产安全保证。

打开：

```text
http://127.0.0.1:8000/api/health
```

你应看到当前演示工作区、运行模式等信息。`mode` 显示 `M0_DETERMINISTIC_DEMO`，这是诚实标识：现在还没调用模型。

## 五、启动前端

在另一个终端：

```powershell
cd product/frontend
npm install
npm run dev
```

浏览器访问 Vite 输出的本地地址，通常是 `http://127.0.0.1:5173`。

查看 `vite.config.ts`：

```typescript
proxy: {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true
  }
}
```

浏览器实际向当前页面的 `/api/tasks` 发请求，Vite 的代理把开发期请求转到 FastAPI。

这意味着前端代码不需要每个组件都写死后端的 IP 和端口。

## 六、第一次点击“开始任务”：发生了什么？

```text
React：
  用户输入任务
      ↓
POST /api/tasks
      ↓
FastAPI：
  生成唯一 task_id
  创建 TaskRecord
  发出 TASK_CREATED 事件
  检查 sample-workspace/calculator.py
  生成 PatchProposal 和真实 Diff
  状态变成 WAITING_APPROVAL
      ↓
React：
  显示 Timeline、Diff、批准/拒绝按钮
```

为什么后端而不是前端负责生成 Diff？

因为后端实际有权限读取受控 Workspace，并能验证当前内容。前端可以渲染 Diff，却不应被当作文件内容和授权状态的权威来源。

## 七、PatchProposal 为什么有 before_sha256？

假设用户看到：

```diff
-    return a - b
+    return a + b
```

但他离开电脑的五分钟里，另一个进程修改了 `calculator.py`。这时原审批提案已经过期。

所以 M0 在准备提案时记录文件文本的哈希，执行前再次检查文件内容与提案创建时一致；如果不一致，拒绝这次写入。

这个设计与我们之前学的 `replace_text` 唯一匹配一起，形成两道保护：

1. 必须是当前批准的文件版本；
2. 待替换旧文本在文件里恰好出现一次。

即便如此，课程 M0 也不把它称为完整 OS 级沙箱或全部并发条件下的事务方案。

## 八、审批的两条路径

### 路径 A：点击“拒绝”

```text
POST /api/tasks/{id}/approval
{"approved": false, "before_sha256": "..."}
      ↓
FastAPI 确认任务仍在 WAITING_APPROVAL
      ↓
状态 REJECTED
      ↓
新增 APPROVAL_DENIED 事件
      ↓
文件字节必须不变
```

这是一条真实的程序逻辑，不是前端假装把按钮关闭。

单元测试 `test_approval_rejection_does_not_modify_file` 使用临时目录，在拒绝前后比较文件字节内容。

### 路径 B：点击“批准并测试”

```text
确认待审批状态与提案哈希
        ↓
apply_proposal()
        ↓
再次解析受控路径
        ↓
文件内容与旧哈希一致吗？
        ↓
旧文本恰好匹配一次吗？
        ↓
同目录临时文件 + os.replace()
        ↓
发出 TOOL_RESULT：真实修改成功
        ↓
run_tests()
        ↓
真实 python -m pytest -q
        ↓
发出 TEST_RESULT + 最终任务状态
```

如果新代码真的满足测试，任务才可能进入 `SUCCEEDED`；如果 pytest FAIL、TIMEOUT 或 ERROR，前端应该显示失败和真实输出。

## 九、SSE 时间线和 TaskRecord 分别是什么？

TaskRecord 包含**后端当前权威状态**。SSE 负责及时通知浏览器：

```text
TASK_CREATED
TOOL_RESULT
APPROVAL_REQUESTED
APPROVAL_ACCEPTED
TEST_STARTED
TEST_RESULT
TASK_FINISHED
```

React 订阅：

```typescript
const stream = new EventSource("/api/tasks/" + taskId + "/events");
```

但 SSE 本质上是通知通道，不是数据库。页面刷新时要重新请求：

```http
GET /api/tasks/{id}
```

M0 将任务保存在当前 Python 进程内存中，所以刷新浏览器通常还在；但**重启后端后可能全部丢失**。因此它还没有满足最终产品的持久化恢复要求。

## 十、第一轮应该怎样验收？

建议按顺序进行：

1. 打开 `/api/health`，确认 Python 后端可访问；
2. 打开 React 页面，确认后端连接信息出现；
3. 提交任务，看到真实 Diff；
4. **先拒绝一次**，确认 `calculator.py` 仍是 `return a - b`；
5. 再创建新任务，点击批准；
6. 观察实际测试日志，确认通过；
7. 检查磁盘上的 `calculator.py` 是否真变成加法；
8. 再发起相同演示任务，应该提示该固定教学 Bug 已不存在，而不能伪造新的修改提案。

这样的顺序能验证**拒绝、执行、测试、重复运行**四种情况。

## 十一、从 M0 升级为真正 Agent，要替换哪里？

主要不是重写整个 React 页面，而是替换谁决定“下一步动作”。

当前：

```text
固定驱动器
  → 已知 calculator.py 的错误
  → 生成固定的替换提案
```

未来：

```text
LLM + LangGraph
  → 动态 search_code / read_file
  → 产生结构化 tool_calls
  → 审批层拦截写入
  → 真实工具执行
  → sync_state
  → completion_guard
```

前端仍显示任务、事件、Diff、审批和测试，只是从固定驱动器换成真正能够处理多种任务的 Agent Core。

此外还要升级：

- HTTP 请求内运行测试 → 后端 Runner 异步调度；
- 进程内存任务列表 → 持久化 Task Store；
- 演示驱动器 → 有真实模型选择与错误处理的工具循环；
- 单次受控替换 → 受控 Repo 检索与多文件修改；
- M0 轻量安全规则 → 经过专门验收的权限、恢复与隔离机制。

## 十二、本章检查题

1. 为什么前端展示的 Diff 不能作为执行权限的唯一依据？
2. TaskRecord 与 SSE 事件的职责为什么不同？
3. 用户拒绝后，模型如果表示“我已经写入”，系统应该相信谁？
4. M0 已经可以在浏览器修改真实文件，为什么仍不该叫作“完成的 Coding Agent”？
5. 从 M0 到 M1，我们是要重写前端，还是把确定性驱动器换成 LangGraph + LLM 的工具执行流程？为什么？

**最重要的认识：完整产品的每个 UI 元素，都必须有一个可追溯的程序事实。**
