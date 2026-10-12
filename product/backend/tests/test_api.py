"""审批 API 测试：拒绝不得造成写入；批准不得使用不匹配的提案摘要。"""

from pathlib import Path

from fastapi.testclient import TestClient

from product.backend.app import main as api


def test_approval_rejection_does_not_modify_file(tmp_path: Path, monkeypatch):
    target = tmp_path / "calculator.py"
    target.write_text("def total(a,b):\n    return a - b\n", encoding="utf-8")
    monkeypatch.setattr(api, "WORKSPACE", tmp_path)
    client = TestClient(api.app)

    created = client.post("/api/tasks", json={"instruction": "修复教学计算错误"})
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "WAITING_APPROVAL"
    before = target.read_bytes()

    denied = client.post(
        f"/api/tasks/{data['task_id']}/approval",
        json={
            "approved": False,
            "before_sha256": data["proposal"]["before_sha256"],
        },
    )
    assert denied.status_code == 200
    assert denied.json()["status"] == "REJECTED"
    assert target.read_bytes() == before


def test_approval_rejects_wrong_hash(tmp_path: Path, monkeypatch):
    target = tmp_path / "calculator.py"
    target.write_text("return a - b\n", encoding="utf-8")
    monkeypatch.setattr(api, "WORKSPACE", tmp_path)
    client = TestClient(api.app)
    data = client.post("/api/tasks", json={"instruction": "修复"}).json()

    response = client.post(
        f"/api/tasks/{data['task_id']}/approval",
        json={"approved": True, "before_sha256": "0" * 64},
    )
    assert response.status_code == 409
    assert target.read_text(encoding="utf-8") == "return a - b\n"


def test_approved_patch_runs_real_pytest(tmp_path: Path, monkeypatch):
    """端到端后端验收：审批 → 真实写文件 → 真实 pytest PASS。"""
    target = tmp_path / "calculator.py"
    target.write_text(
        "def calculate_total(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (tmp_path / "test_calculator.py").write_text(
        "from calculator import calculate_total\n"
        "def test_total():\n    assert calculate_total(6, 4) == 10\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "WORKSPACE", tmp_path)
    client = TestClient(api.app)

    created = client.post("/api/tasks", json={"instruction": "修复并测试"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "WAITING_APPROVAL"
    assert "return a - b" in target.read_text(encoding="utf-8")

    approved = client.post(
        f"/api/tasks/{task['task_id']}/approval",
        json={
            "approved": True,
            "before_sha256": task["proposal"]["before_sha256"],
        },
    )
    assert approved.status_code == 200
    result = approved.json()
    assert result["status"] == "SUCCEEDED"
    assert result["test_result"]["status"] == "PASS"
    assert "return a + b" in target.read_text(encoding="utf-8")
    assert any(e["kind"] == "TEST_RESULT" for e in result["events"])


def test_repeating_approval_is_rejected(tmp_path: Path, monkeypatch):
    """一次审批提交不能重复完成两次。"""
    target = tmp_path / "calculator.py"
    target.write_text("return a - b\n", encoding="utf-8")
    monkeypatch.setattr(api, "WORKSPACE", tmp_path)
    client = TestClient(api.app)
    task = client.post("/api/tasks", json={"instruction": "修复"}).json()
    payload = {
        "approved": False,
        "before_sha256": task["proposal"]["before_sha256"],
    }
    first = client.post(f"/api/tasks/{task['task_id']}/approval", json=payload)
    second = client.post(f"/api/tasks/{task['task_id']}/approval", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
    assert target.read_text(encoding="utf-8") == "return a - b\n"
