# 复习归档：真实 DeepSeek + LangGraph 基础 Agent Loop

> 2026-11-03 课程校准：**这部分属于既有知识复习，不再作为下一节主课**。本页仍保留技术要点供查阅；课堂下一阶段直接进入 Harness 的完成证据与执行可靠性。此前代码尚未运行验证。

## 本课要解决的问题
固定的 `LLM → Tool → LLM` 不能动态决定是否继续执行。使用 `StateGraph` 和条件边实现 `llm → tools → llm`，模型通过 `AIMessage.tool_calls` 提出请求，Harness 根据调用次数和权限决定是否执行。

## 关键机制
- `messages: Annotated[list[AnyMessage], add_messages]`：将新的消息合并进状态，保留模型请求与工具响应。
- `tool_rounds: int`：由执行工具的节点更新，作为真实工具执行轮次的计数。
- `bind_tools([read_file])`：向模型声明可用工具；**不执行工具**。
- `ToolNode([read_file])`：实际执行工具并生成匹配 `tool_call_id` 的 `ToolMessage`。
- 条件边：最后一条 `AIMessage.tool_calls` 存在才考虑进入 tools，否则 END；到达执行上限要明确处理。
- `max_retries=0`、`recursion_limit`：学习阶段控制额外请求与执行循环；不替代权限校验。

## 实战约定
- 直接使用真实 DeepSeek；课堂先在独立 Python 文件中运行，不急于接 React。
- 只允许 read_file 读取教学工作区 `calculator.py`，禁止写入、Shell 和越界路径。
- 最大工具执行轮数为 2。模型无工具调用时允许正常结束，但不能声称读过文件。
- 正常完整轨迹：HumanMessage → AIMessage(tool_calls) → ToolMessage → AIMessage(最终回答)。要核对原始 call ID 对应关系。
- 一次测试通常产生至少两次付费模型请求；不要连续盲目重试。
- 待学习者手写：`route_after_llm`、两条关键边；错误先定位模型响应、消息格式、条件边或工具执行哪个层次。

## 核心架构问题
1. 为什么 `tool_rounds` 不能让模型自己决定？
2. 为什么 `tool_calls` 是意图而不是文件读取证据？
3. 工具执行完成后为什么需要回到模型节点？
4. 为什么同时需要条件边、工具轮数限制及 `recursion_limit`？
5. 模型未请求工具和 Harness 拒绝工具，有何不同？

## 课后验证模板
记录实际 `AIMessage.tool_calls`、ToolMessage 的 `tool_call_id`、工具轮数和最终分析；分清已测试与未测试。根据本地源码与真实模型运行结果追加复盘。
