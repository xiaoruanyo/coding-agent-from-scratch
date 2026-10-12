"""M0 的基础工具测试：所有修改都只发生在 pytest 的临时目录。"""

from pathlib import Path

import pytest

from product.backend.app.core import (
    apply_proposal,
    authorized_path,
    make_demo_proposal,
    read_text,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "calculator.py").write_text(
        "def total(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    return tmp_path


def test_authorized_path_rejects_parent_traversal(workspace: Path):
    with pytest.raises(ValueError):
        authorized_path(workspace, "../secret.txt")


def test_authorized_path_rejects_absolute_path(workspace: Path):
    with pytest.raises(ValueError):
        authorized_path(workspace, str((workspace / "calculator.py").resolve()))


def test_unique_patch_succeeds(workspace: Path):
    proposal = make_demo_proposal(workspace)
    result = apply_proposal(workspace, proposal)
    assert result["status"] == "SUCCESS"
    assert "return a + b" in read_text(workspace, "calculator.py")


def test_stale_patch_is_rejected_without_writing(workspace: Path):
    proposal = make_demo_proposal(workspace)
    target = workspace / "calculator.py"
    target.write_text("def total(a, b):\n    return 999\n", encoding="utf-8")
    before = target.read_bytes()

    with pytest.raises(ValueError, match="文件内容已改变"):
        apply_proposal(workspace, proposal)
    assert target.read_bytes() == before


def test_patch_rejects_multiple_old_matches(workspace: Path):
    (workspace / "calculator.py").write_text(
        "def total(a, b):\n    return a - b\n    return a - b\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="唯一"):
        make_demo_proposal(workspace)


def test_existing_symlink_outside_workspace_is_rejected(workspace: Path, tmp_path: Path):
    outside = tmp_path.parent / ("mini-outside-" + tmp_path.name)
    outside.write_text("secret", encoding="utf-8")
    try:
        link = workspace / "escape.py"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("当前系统不允许创建测试符号链接")
        with pytest.raises(ValueError):
            authorized_path(workspace, "escape.py")
    finally:
        outside.unlink(missing_ok=True)
