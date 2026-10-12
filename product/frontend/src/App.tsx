import { useEffect, useState } from "react";

type Status = "RUNNING" | "WAITING_APPROVAL" | "SUCCEEDED" | "FAILED" | "REJECTED" | "UNVERIFIED";
type EventItem = { id: number; time: string; kind: string; message: string; data: Record<string, unknown> };
type Proposal = { path: string; old_text: string; new_text: string; before_sha256: string; diff: string };
type TestResult = { status: string; exit_code: number | null; output: string };
type Task = {
  task_id: string;
  instruction: string;
  created_at: string;
  status: Status;
  events: EventItem[];
  proposal: Proposal | null;
  test_result: TestResult | null;
  error: string | null;
};
type Summary = Pick<Task, "task_id" | "instruction" | "created_at" | "status">;
type Health = { workspace: string; warning: string; mode: string; status: string };

const STATUS: Record<Status, string> = {
  RUNNING: "执行中",
  WAITING_APPROVAL: "等待审批",
  SUCCEEDED: "测试通过",
  FAILED: "执行失败",
  REJECTED: "已拒绝",
  UNVERIFIED: "未验证"
};
const TERMINAL: Status[] = ["SUCCEEDED", "FAILED", "REJECTED", "UNVERIFIED"];

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const result = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }
  });
  if (!result.ok) {
    const error = await result.json().catch(() => null);
    throw new Error(String(error?.detail ?? result.statusText));
  }
  return (await result.json()) as T;
}

function time(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString("zh-CN");
}

function Diff({ source }: { source: string }) {
  return (
    <div className="diff" role="region" aria-label="文件修改差异">
      {source.split("\n").map((line, index) => {
        const tone = line.startsWith("+") ? "added" : line.startsWith("-") ? "removed" : line.startsWith("@@") ? "marker" : "";
        return <div className={"diff-line " + tone} key={index}>{line || "\u00a0"}</div>;
      })}
    </div>
  );
}

export default function App() {
  const [instruction, setInstruction] = useState("请修复计算函数的 Bug，先让我审批修改，再运行测试。");
  const [health, setHealth] = useState<Health | null>(null);
  const [history, setHistory] = useState<Summary[]>([]);
  const [task, setTask] = useState<Task | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const currentId = task?.task_id ?? "";

  async function refreshHistory() {
    setHistory(await api<Summary[]>("/api/tasks"));
  }

  useEffect(() => {
    api<Health>("/api/health").then(setHealth).catch((e: unknown) => setError(String(e)));
    refreshHistory().catch((e: unknown) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!currentId) return;
    let disposed = false;
    const refresh = async () => {
      try {
        const latest = await api<Task>("/api/tasks/" + currentId);
        if (!disposed) setTask(latest);
      } catch (e) {
        if (!disposed) setError(String(e));
      }
    };
    const stream = new EventSource("/api/tasks/" + currentId + "/events");
    stream.addEventListener("task", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as EventItem;
      void refresh();
      if (["TASK_FINISHED", "APPROVAL_DENIED", "TASK_STOPPED"].includes(data.kind)) {
        stream.close();
        void refreshHistory();
      }
    });
    void refresh();
    return () => {
      disposed = true;
      stream.close();
    };
  }, [currentId]);

  async function start() {
    if (busy || !instruction.trim()) return;
    setBusy(true);
    setError("");
    try {
      const created = await api<Task>("/api/tasks", {
        method: "POST",
        body: JSON.stringify({ instruction: instruction.trim() })
      });
      setTask(created);
      await refreshHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function approve(value: boolean) {
    if (!task?.proposal || busy) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<Task>("/api/tasks/" + task.task_id + "/approval", {
        method: "POST",
        body: JSON.stringify({
          approved: value,
          before_sha256: task.proposal.before_sha256
        })
      });
      setTask(updated);
      await refreshHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function openTask(id: string) {
    setError("");
    try {
      setTask(await api<Task>("/api/tasks/" + id));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">◇</div>
          <div>
            <strong>Mini Coding Agent</strong>
            <small>从原理到完整产品</small>
          </div>
        </div>
        <div className="side-heading">本地演示工作区</div>
        <div className="workspace">
          <span className="folder-icon">▣</span>
          <div>
            <strong>sample-workspace</strong>
            <small title={health?.workspace}>{health?.workspace ?? "正在连接后端..."}</small>
          </div>
        </div>
        <div className="side-heading history-heading">任务历史 <span>{history.length}</span></div>
        <div className="history">
          {history.length === 0 && <p className="empty-small">暂无任务记录</p>}
          {history.map((item) => (
            <button
              className={"history-item " + (currentId === item.task_id ? "selected" : "")}
              key={item.task_id}
              onClick={() => void openTask(item.task_id)}
            >
              <strong>{item.instruction}</strong>
              <small>{time(item.created_at)} · {STATUS[item.status]}</small>
            </button>
          ))}
        </div>
        <div className="sidebar-footer"><span className="signal" /> M0 教学原型 · 本地运行</div>
      </aside>

      <main className="content">
        <header className="page-header">
          <div>
            <span className="eyebrow">LEARNING PROJECT / MILESTONE 0</span>
            <h1>让 Agent 真正接触代码</h1>
            <p>先验证网页、审批、真实文件修改与 pytest，再接入 LangGraph 和模型自主规划。</p>
          </div>
          <div className="online"><span className="signal" /> {health ? "已连接本地后端" : "检查连接中"}</div>
        </header>

        <section className="card task-compose">
          <label htmlFor="instruction">给 Mini Coding Agent 一个任务</label>
          <textarea
            id="instruction"
            rows={3}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="描述你需要修复的代码问题..."
          />
          <div className="compose-bottom">
            <span>当前使用固定教学 Bug 驱动器，不执行任意模型 Shell。</span>
            <button className="primary" disabled={busy} onClick={() => void start()}>
              {busy ? "处理中..." : "开始任务 →"}
            </button>
          </div>
        </section>

        {error && <div className="error-box" role="alert">操作失败：{error}</div>}

        <div className="panels">
          <section className="card panel">
            <div className="panel-head">
              <div><span className="eyebrow">TASK TIMELINE</span><h2>Agent 执行过程</h2></div>
              {task && <span className={"status " + task.status.toLowerCase()}>{STATUS[task.status]}</span>}
            </div>
            {!task ? (
              <div className="empty">
                <span className="empty-symbol">⌘</span>
                <h3>从真实任务开始</h3>
                <p>提交任务后，这里会展示来自后端的事件，而不是预先写好的模拟日志。</p>
              </div>
            ) : (
              <>
                <div className="metadata">任务 {task.task_id.slice(0, 10)} · {time(task.created_at)}</div>
                <div className="timeline">
                  {task.events.map((event) => (
                    <div className="timeline-item" key={event.id}>
                      <div className="step-dot" />
                      <div>
                        <div className="event-row"><strong>{event.message}</strong><time>{time(event.time)}</time></div>
                        <small>{event.kind}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>

          <section className="card panel">
            <div className="panel-head">
              <div><span className="eyebrow">CHANGE REVIEW / TESTS</span><h2>变更审核与验证</h2></div>
            </div>
            {!task?.proposal ? (
              <div className="empty">
                <span className="empty-symbol">▤</span>
                <h3>还没有待审核的变更</h3>
                <p>Agent 生成真实修改提案后，会在这里展示具体差异。</p>
              </div>
            ) : (
              <div className="review">
                <div className="filename"><span className="py">PY</span><strong>{task.proposal.path}</strong> <small>修改预览</small></div>
                <Diff source={task.proposal.diff} />
                {task.status === "WAITING_APPROVAL" && (
                  <div className="approval">
                    <div><strong>等待你的批准</strong><p>只批准本次展示的具体文件和内容。</p></div>
                    <div className="action-row">
                      <button className="secondary" disabled={busy} onClick={() => void approve(false)}>拒绝</button>
                      <button className="primary" disabled={busy} onClick={() => void approve(true)}>批准并测试</button>
                    </div>
                  </div>
                )}
                <div className="test-area">
                  <div className="test-head"><h3>真实测试结果</h3><span>{task.test_result?.status ?? "NOT_RUN"}</span></div>
                  {task.test_result ? (
                    <>
                      <div className="metadata">pytest 退出码：{String(task.test_result.exit_code)}</div>
                      <pre>{task.test_result.output}</pre>
                    </>
                  ) : <p className="muted">{task.status === "REJECTED" ? "修改被拒绝；没有执行文件写入或测试。" : "尚未运行测试，不能视为修复成功。"}</p>}
                </div>
              </div>
            )}
          </section>
        </div>
        <footer>教学原型 M0 · 真实文件与测试 · LangGraph/LLM 自主执行属于后续里程碑</footer>
      </main>
    </div>
  );
}
