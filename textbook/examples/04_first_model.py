"""N02：Chat Model 返回 AIMessage；本脚本会实际调用外部 API。"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI


def main():
    load_dotenv()

    key = os.getenv("DEEPSEEK_API_KEY")
    model_name = os.getenv("DEEPSEEK_MODEL")
    if not key or not model_name:
        raise RuntimeError("请先配置 DEEPSEEK_API_KEY 和 DEEPSEEK_MODEL")

    model = ChatOpenAI(
        model=model_name,
        api_key=key,
        base_url="https://api.deepseek.com",
        temperature=0,
    )

    response = model.invoke(
        [HumanMessage(content="请用一句话解释 LangGraph 是什么")]
    )
    print("回复对象类型:", type(response).__name__)
    print("正文:", response.content)
    print("tool_calls:", response.tool_calls)
    print("metadata:", response.response_metadata)


if __name__ == "__main__":
    main()
