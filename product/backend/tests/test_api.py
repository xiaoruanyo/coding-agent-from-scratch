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
