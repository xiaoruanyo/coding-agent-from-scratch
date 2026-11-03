"""M1 DeepSeek 分析接口测试：全部使用 Mock 模型，不访问真实 API。"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from product.backend.app import llm
from product.backend.app import main as api


class FakeChatModel:
    """替代 ChatDeepSeek 的最小假模型，记录构造参数与消息。"""

    last_kwargs: dict[str, Any] = {}
    last_messages: list[Any] = []
    response_text = "任务分析结果"
    error: Exception | None = None

    def __init__(self, **kwargs: Any):
        type(self).last_kwargs = kwargs

    def invoke(self, messages: list[Any]) -> AIMessage:
        type(self).last_messages = list(messages)
        if type(self).error is not None:
            raise type(self).error
        return AIMessage(content=type(self).response_text)


@pytest.fixture
def mocked_llm(monkeypatch: pytest.MonkeyPatch) -> type[FakeChatModel]:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    monkeypatch.setattr(llm, "ChatDeepSeek", FakeChatModel)
    FakeChatModel.last_kwargs = {}
    FakeChatModel.last_messages = []
    FakeChatModel.response_text = "任务分析结果"
    FakeChatModel.error = None
    return FakeChatModel


def test_analyze_returns_model_analysis(mocked_llm: type[FakeChatModel]):
    client = TestClient(api.app)

    response = client.post("/api/llm/analyze", json={"instruction": "  分析登录模块的测试覆盖  "})

    assert response.status_code == 200
    assert response.json() == {"analysis": "任务分析结果", "model": "deepseek-flash"}
    assert mocked_llm.last_kwargs["model"] == "deepseek-flash"
    assert mocked_llm.last_kwargs["timeout"] == llm.REQUEST_TIMEOUT_SECONDS
    assert mocked_llm.last_kwargs["max_retries"] == llm.MAX_RETRIES
    human_messages = [m for m in mocked_llm.last_messages if isinstance(m, HumanMessage)]
    assert human_messages[0].content == "分析登录模块的测试覆盖"
    assert "test-key-not-real" not in response.text


def test_blank_instruction_is_rejected_before_model_call(mocked_llm: type[FakeChatModel]):
    client = TestClient(api.app)

    response = client.post("/api/llm/analyze", json={"instruction": "   \n\t "})

    assert response.status_code == 422
    assert mocked_llm.last_kwargs == {}


def test_missing_api_key_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch, mocked_llm: type[FakeChatModel]
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(api.app)

    response = client.post("/api/llm/analyze", json={"instruction": "分析任务"})

    assert response.status_code == 503
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]
    assert mocked_llm.last_kwargs == {}


def test_model_failure_does_not_leak_details(mocked_llm: type[FakeChatModel]):
    mocked_llm.error = RuntimeError("upstream failed with key sk-test-secret")
    client = TestClient(api.app)

    response = client.post("/api/llm/analyze", json={"instruction": "分析任务"})

    assert response.status_code == 502
    assert "模型调用失败" in response.json()["detail"]
    assert "sk-test-secret" not in response.text


def test_empty_model_output_is_treated_as_failure(mocked_llm: type[FakeChatModel]):
    mocked_llm.response_text = "   "
    client = TestClient(api.app)

    response = client.post("/api/llm/analyze", json={"instruction": "分析任务"})

    assert response.status_code == 502
    assert "空分析" in response.json()["detail"]
