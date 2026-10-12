# 产品阶段 · 第一条可运行的全栈链路

> **这是产品化阶段的里程碑 M0：确定性演示驱动器 + 真实文件操作 + FastAPI + React。**  
> 它**不是已经完成的通用 Coding Agent**。M0 用可复现的固定 Bug 修复示例证明浏览器、后端、审批、真实修改和真实 pytest 已经能够贯通。随后课程会把确定性演示驱动器换成 LangGraph + LLM 的动态规划执行器，并补充持久化与完整安全验收。

为什么先做 M0？如果第一次集成就同时调试模型、工具调用、Checkpoint、HTTP、SSE、React 和 pytest，任何错误都很难定位。先把产品通道跑通，后面每层只替换一个职责。

## 最终要做的产品

参见 [产品契约](../docs/PRODUCT.md)、[架构](../docs/ARCHITECTURE.md)、[毕业验收](../docs/DEFINITION-OF-DONE.md)。

M0 当前实现的真实能力：

- 本地 FastAPI API 与 React + TypeScript 页面；
- 固定授权演示工作区；
- 任务创建与历史任务列表（进程内存）；
- 演示驱动器定位固定的 `calculator.py` Bug，生成真实 Diff 提案；
- **后端强制审批**：用户拒绝则不执行修改；
- 批准后再次校验旧文本唯一匹配，使用临时文件替换目标文件；
- 运行真实 `python -m pytest -q`，显示退出码、测试结果与有限输出；
- 通过 SSE 传送任务事件，刷新页面可从后端查询任务状态（仅当前进程有效）。

M0 明确**还没有**：

- 真实 LLM 推理、Tool Calling 与 LangGraph 驱动；
- 多种未知 Bug 的自主定位和修复；
- 持久化 Checkpointer、后端重启恢复；
- 多用户授权、生产级沙箱与不可信代码隔离；
- 足够严密的并发文件操作与 OS 级 TOCTOU 防护。

## 目录

```text
product/
├── backend/
│   ├── app/
│   │   ├── core.py       # 真实受限工具能力
│   │   └── main.py       # 任务、审批与 SSE API
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   └── package.json
└── sample-workspace/
    ├── calculator.py
    └── test_calculator.py
```

## 启动（Windows PowerShell）

从仓库根目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r product/backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn product.backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

新开一个终端：

```powershell
cd product/frontend
npm install
npm run dev
```

打开前端显示的本地 URL（默认 Vite 5173），Vite 开发代理把 `/api` 转发给 `127.0.0.1:8000`。

### 第一次体验

1. 输入“请修复计算函数并运行测试”。
2. 观察 UI 的任务和工具事件。
3. 看到 `calculator.py` 的一行 Diff。
4. 点击拒绝：不应产生文件变更。重新创建任务可再做批准。
5. 点击批准：执行实际文件修改并运行真正 pytest，UI 展示 PASS 或 FAIL。

第一次批准成功后，演示工作区的 Bug 会被修复。若想重新体验，从 Git 恢复样例文件或在自己专用的演示目录中把 `return a + b` 改回 `return a - b`；不要在真实项目上执行重置命令。

## 离线后端验收

```powershell
.\.venv\Scripts\python.exe -m pytest product/backend/tests -q
```

这些测试通过临时目录验证路径边界、精确修改与拒绝审批等基本行为，**不会触碰真实工作项目**。

## 后续课程如何逐步把它变成完整 Agent

M1：以 LangGraph 驱动动态任务，加入真实 LLM、Tool Calling、Checkpoint。  
M2：使用独立 `approval_gate`、多 Tool Calls 完整结果配对，严格的 `sync_state` 和 Completion Guard。  
M3：持久化任务、Checkpointer、断线重连、任务取消与恢复。  
M4：Code Search、AST Repo Map、Working Summary 和更完整的工具链。  
M5：达到全部端到端安全、真实测试与 UI 验收条款，才宣布 Mini Coding Agent V1 完成。

本地优先不等于安全沙箱。**本演示只允许执行自己信任的教学仓库。**
