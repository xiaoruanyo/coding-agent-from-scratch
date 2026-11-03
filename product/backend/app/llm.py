"""M1：使用 DeepSeek 对任务描述做单轮分析。

本模块只把用户提供的描述发送给模型，不读取仓库、不执行工具，
也不参与 M0 的任务创建、审批、文件修改与测试流程。
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek

MODEL_ID = "deepseek-flash"
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_RETRIES = 2

SYSTEM_PROMPT = """你是 Mini Coding Agent 的任务分析助手。
请只依据用户给出的任务描述，用中文输出简洁的分析，包含：
1. 对任务目标的理解；
2. 可能涉及的代码范围（仅根据描述推断，不得声称已读取、搜索或检查任何仓库文件）；
3. 建议的验证方式；
4. 风险、假设和需要用户补充的信息。

不得声称执行过任何工具、命令、测试或文件读取。信息不足时要明确指出，不要编造仓库内容。"""


class LLMConfigurationError(RuntimeError):
    """服务端没有配置模型凭证。"""


class LLMInvocationError(RuntimeError):
    """模型调用失败；消息中不包含底层异常细节。"""


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts).strip()
    return str(content).strip()


def analyze_task(instruction: str) -> str:
    """调用 DeepSeek 分析任务描述，返回中文分析文本。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise LLMConfigurationError("未配置 DEEPSEEK_API_KEY，无法调用模型")

    try:
        model = ChatDeepSeek(
            model=MODEL_ID,
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
        )
        response = model.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=instruction),
            ]
        )
    except Exception as exc:  # 把供应商异常转换为不含敏感信息的接口错误
        raise LLMInvocationError(f"模型调用失败（{type(exc).__name__}）") from exc

    text = _extract_text(response)
    if not text:
        raise LLMInvocationError("模型返回了空分析")
    return text
