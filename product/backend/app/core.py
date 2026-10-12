"""可核验的最小工作区工具。仅适用于可信的本地练习目录。

M0 的路径检查并不构成防御攻击者并发替换文件的 OS 沙箱。
生产场景还需目录文件句柄、隔离、权限降级和更强 TOCTOU 防护。
"""

from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 512 * 1024
MAX_TEST_OUTPUT = 5000
MAX_TEST_SECONDS = 20
OLD_LINE = "return a - b"
NEW_LINE = "return a + b"


@dataclass(frozen=True)
class PatchProposal:
    path: str
    old_text: str
    new_text: str
    before_sha256: str
    diff: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "before_sha256": self.before_sha256,
            "diff": self.diff,
        }


def authorized_path(workspace: Path, relative_path: str, *, must_exist: bool = True) -> Path:
    """限制相对路径于 workspace 中，拒绝现有符号链接逃逸。"""
    root = workspace.resolve()
    candidate_input = Path(relative_path)
    if not relative_path.strip() or candidate_input.is_absolute():
        raise ValueError("必须提供非空的工作区相对路径")

    candidate = (root / candidate_input).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("路径不在授权工作区内")
    if must_exist and not candidate.is_file():
        raise ValueError("目标不是存在的普通文件")
    return candidate


def read_text(workspace: Path, relative_path: str) -> str:
    path = authorized_path(workspace, relative_path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("文件超过读取上限")
    return path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_demo_proposal(workspace: Path) -> PatchProposal:
    """只为课程样例生成确定性的修改计划；不使用 LLM。"""
    rel = "calculator.py"
    before = read_text(workspace, rel)
    if before.count(OLD_LINE) != 1:
        raise ValueError("没有发现可唯一修复的教学 Bug；文件可能已经修复")
    after = before.replace(OLD_LINE, NEW_LINE, 1)
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/" + rel,
            tofile="b/" + rel,
        )
    )
    return PatchProposal(
        path=rel,
        old_text=OLD_LINE,
        new_text=NEW_LINE,
        before_sha256=sha256_text(before),
        diff=diff,
    )


def apply_proposal(workspace: Path, proposal: PatchProposal) -> dict:
    """审批后仍检查文件版本与唯一旧文本，防止沿用过期提案。

    在同目录创建临时文件，然后替换目标。适用于受信任的练习工作区。
    """
    target = authorized_path(workspace, proposal.path)
    before = read_text(workspace, proposal.path)
    if sha256_text(before) != proposal.before_sha256:
        raise ValueError("文件内容已改变：原审批提案失效，请重新生成")
    if before.count(proposal.old_text) != 1:
        raise ValueError("待替换旧文本必须恰好匹配一次")

    after = before.replace(proposal.old_text, proposal.new_text, 1)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=".mini-agent-",
            suffix=".tmp",
            delete=False,
        ) as file:
            file.write(after)
            temp_name = file.name
        # 再查一次；仍不意味着阻止全部 OS 级并发替换，M0 明确非沙箱。
        if authorized_path(workspace, proposal.path) != target:
            raise ValueError("目标路径发生改变")
        os.replace(temp_name, target)
        temp_name = None
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"status": "SUCCESS", "path": proposal.path, "sha256": sha256_text(after)}


def run_tests(workspace: Path) -> dict:
    """执行受信任样例仓库的 pytest；固定参数，不接受 LLM 指令或 Shell。"""
    try:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workspace.resolve(),
            text=True,
            capture_output=True,
            timeout=MAX_TEST_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or b""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        return {
            "status": "TIMEOUT",
            "exit_code": None,
            "output": str(partial)[-MAX_TEST_OUTPUT:],
        }
    except OSError as exc:
        return {"status": "ERROR", "exit_code": None, "output": str(exc)}

    # pytest 退出码 1 为测试断言失败；其他错误不笼统视为普通 FAIL。
    if done.returncode == 0:
        status = "PASS"
    elif done.returncode == 1:
        status = "FAIL"
    else:
        status = "ERROR"
    output = (done.stdout + "\n" + done.stderr)[-MAX_TEST_OUTPUT:]
    return {"status": status, "exit_code": done.returncode, "output": output}
