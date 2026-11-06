"""大模型调用出口。

所有 AI 请求只能从这里出去，统一做超时、重试、熔断、指标和日志。

三个入口：
- `complete(system, user)`：单轮问答，询问中心等场景使用
- `complete_chat(messages)`：完整 messages 数组，非流式多轮使用
- `stream_with_tools(messages, tools)`：流式 + 工具调用，Agent 对话使用
"""

import asyncio

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError
from app.core.metrics import AI_CALLS, AI_CIRCUIT_OPEN
from app.modules.ai.breaker import OPEN, CircuitBreaker

logger = structlog.get_logger("ai")

breaker = CircuitBreaker(
    failure_threshold=settings.AI_FAILURE_THRESHOLD,
    recovery_timeout=settings.AI_RECOVERY_SECONDS,
)

_MAX_ATTEMPTS = 2


def _build_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=30.0,
    )


async def _call(messages: list[dict[str, str]]) -> str:
    """真正发起一次模型调用。

    空内容当失败处理：有些供应商会在限流时返回空 choices。
    """
    client = _build_client()    #得到模型实例
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.7,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI 返回了空内容")
    return content


async def complete_chat(messages: list[dict[str, str]]) -> str:
    """按完整 messages 调用模型。

    熔断、重试、指标和 `complete` 共用一套逻辑。
    """
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)

    if not breaker.allow_request():
        AI_CALLS.labels("circuit_open").inc()
        AI_CIRCUIT_OPEN.set(1)
        logger.warning("ai.circuit_open")
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            reply = await _call(messages)
            breaker.record_success()
            AI_CALLS.labels("success").inc()
            AI_CIRCUIT_OPEN.set(0)
            return reply
        except Exception as exc:  # noqa: BLE001 - 外部依赖，任何失败都重试一次
            last_error = exc
            logger.warning("ai.call_failed", attempt=attempt, error=repr(exc))
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(0.5)

    breaker.record_failure()
    AI_CALLS.labels("failure").inc()
    if breaker.current_state() == OPEN:
        AI_CIRCUIT_OPEN.set(1)
    logger.error("ai.unavailable", attempts=_MAX_ATTEMPTS)
    raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from last_error


async def complete(*, system: str, user: str) -> str:
    """单轮调用，保持原有签名不变。"""
    return await complete_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )


async def stream_with_tools(messages: list[dict], tools: list[dict]):
    """流式调用，同时支持工具调用。

    产出的两种事件：
    - ("delta", 文本片段)：正常内容，边生成边推给客户端
    - ("tool_calls", [{id, name, arguments}, ...])：
      本轮结束时模型要求调用工具，由调用方执行后再继续下一轮

    注意：流一旦开始就无法重试；中途失败会抛 AppError，
    调用方需要保留已经输出的内容。
    """
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)

    if not breaker.allow_request():  # 熔断器
        AI_CALLS.labels("circuit_open").inc()
        AI_CIRCUIT_OPEN.set(1)
        logger.warning("ai.circuit_open")
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    try:
        stream = await _build_client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            stream=True,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
        )

        # 工具调用在流里是「增量片段」，需要按 index 拼起来
        calls: dict[int, dict] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                yield ("delta", delta.content)

            for tool_call in delta.tool_calls or []:
                entry = calls.setdefault(
                    tool_call.index,
                    {"id": "", "name": "", "arguments": ""},
                )
                if tool_call.id:
                    entry["id"] = tool_call.id
                if tool_call.function:
                    if tool_call.function.name:
                        entry["name"] += tool_call.function.name
                    if tool_call.function.arguments:
                        entry["arguments"] += tool_call.function.arguments

        if calls:
            yield ("tool_calls", [calls[i] for i in sorted(calls)])

        breaker.record_success()
        AI_CALLS.labels("success").inc()
        AI_CIRCUIT_OPEN.set(0)
    except Exception as exc:  # noqa: BLE001
        breaker.record_failure()
        AI_CALLS.labels("failure").inc()
        logger.warning("ai.stream_failed", error=repr(exc))
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from exc
