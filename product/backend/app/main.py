"""Mini Coding Agent M0 的本地 HTTP API。

注意：M0 用固定的教学 Bug 驱动器，不是通用 LLM Agent。
任务和事件只存当前进程内存，演示刷新后恢复，不承诺重启恢复。
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .core import PatchProposal, apply_proposal, make_demo_proposal, run_tests

WORKSPACE = Path(__file__).resolve().parents[2] / "sample-workspace"
app = FastAPI(title="Mini Coding Agent M0", version="0.1.0")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TaskRecord:
    task_id: str
    instruction: str
    status: str = "RUNNING"
    proposal: PatchProposal | None = None
    test_result: dict | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def emit(self, kind: str, message: str, **data: Any) -> None:
        self.events.append(
            {
                "id": len(self.events) + 1,
                "time": utc_now(),
                "kind": kind,
                "message": message,
                "data": data,
            }
        )

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "status": self.status,
            "created_at": self.created_at,
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "test_result": self.test_result,
            "error": self.error,
            "events": list(self.events),
        }


TASKS: dict[str, TaskRecord] = {}
TASKS_LOCK = threading.RLock()
TERMINAL = {"SUCCEEDED", "FAILED", "REJECTED", "UNVERIFIED"}


class StartTask(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)


class ApprovalDecision(BaseModel):
    approved: bool
    before_sha256: str = Field(min_length=64, max_length=64)


def get_record(task_id: str) -> TaskRecord:
    with TASKS_LOCK:
        record = TASKS.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return record


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "M0_DETERMINISTIC_DEMO",
        "workspace": str(WORKSPACE.resolve()),
        "warning": "仅用于可信本地示例；当前未接入 LLM，也未提供持久化恢复",
    }


@app.get("/api/tasks")
def list_tasks() -> list[dict]:
    with TASKS_LOCK:
        records = list(TASKS.values())[-50:]
    return [
        {
            "task_id": record.task_id,
            "status": record.status,
            "instruction": record.instruction,
            "created_at": record.created_at,
        }
        for record in reversed(records)
    ]


@app.post("/api/tasks", status_code=201)
def start_task(body: StartTask) -> dict:
    task = TaskRecord(
        task_id=uuid.uuid4().hex,
        instruction=body.instruction.strip(),
    )
    with TASKS_LOCK:
        TASKS[task.task_id] = task

    with task.lock:
        task.emit("TASK_CREATED", "已创建本地教学任务")
        task.emit(
            "TOOL_RESULT",
            "教学驱动器在已授权工作区检查 calculator.py",
            tool="read_file",
            path="calculator.py",
        )
        try:
            task.proposal = make_demo_proposal(WORKSPACE)
            task.status = "WAITING_APPROVAL"
            task.emit(
                "APPROVAL_REQUESTED",
                "已经生成真实 Diff，等待用户审批具体修改",
                path=task.proposal.path,
                diff=task.proposal.diff,
            )
        except (OSError, ValueError, UnicodeError) as exc:
            task.status = "UNVERIFIED"
            task.error = str(exc)
            task.emit("TASK_STOPPED", "未产生安全、唯一的修改提案", reason=task.error)
        return task.as_dict()


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = get_record(task_id)
    with task.lock:
        return task.as_dict()


@app.post("/api/tasks/{task_id}/approval")
def decide_approval(task_id: str, body: ApprovalDecision) -> dict:
    task = get_record(task_id)
    with task.lock:
        if task.status != "WAITING_APPROVAL" or task.proposal is None:
            raise HTTPException(status_code=409, detail="任务当前不在待审批状态")

        if body.before_sha256 != task.proposal.before_sha256:
            raise HTTPException(status_code=409, detail="审批请求与当前提案不一致")

        if not body.approved:
            task.status = "REJECTED"
            task.emit("APPROVAL_DENIED", "用户拒绝：本次文件修改未执行")
            return task.as_dict()

        task.status = "RUNNING"
        task.emit("APPROVAL_ACCEPTED", "用户批准这一次具体文件修改")
        try:
            result = apply_proposal(WORKSPACE, task.proposal)
            task.emit(
                "TOOL_RESULT", "文件已经真实修改", tool="replace_text", result=result
            )
        except (OSError, ValueError, UnicodeError) as exc:
            task.status = "FAILED"
            task.error = str(exc)
            task.emit("TOOL_ERROR", "文件修改失败", error=task.error)
            return task.as_dict()

        # M0 的 HTTP 审批请求会等待测试完成；后续由 Runner 异步调度。
        task.emit("TEST_STARTED", "开始运行受限的本地 pytest")
        task.test_result = run_tests(WORKSPACE)
        task.emit(
            "TEST_RESULT",
            "pytest 已结束，以下为真实执行结果",
            result=task.test_result,
        )
        if task.test_result["status"] == "PASS":
            task.status = "SUCCEEDED"
            task.emit("TASK_FINISHED", "已修改文件，当前工作区测试通过")
        else:
            task.status = "FAILED"
            task.emit(
                "TASK_FINISHED",
                "未能获得测试通过证据，不能宣称修复成功",
                test_status=task.test_result["status"],
            )
        return task.as_dict()


@app.get("/api/tasks/{task_id}/events")
async def stream_events(task_id: str, after: int = Query(default=0, ge=0)):
    """SSE 发送任务事件。M0 用内存列表保存历史，允许 after 重连。

    生产版需要持久化事件日志，并处理慢消费者和断线资源占用。
    """
    task = get_record(task_id)

    async def generator():
        cursor = after
        while True:
            with task.lock:
                pending = [event for event in task.events if event["id"] > cursor]
                status = task.status

            for item in pending:
                cursor = item["id"]
                yield (
                    f"id: {item['id']}\n"
                    "event: task\n"
                    f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                )

            if status in TERMINAL and not pending:
                break

            await asyncio.sleep(0.35)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
