"""大模型调用出口。

所有 AI 请求只能从这里出去，统一做超时、重试、熔断、指标和日志。

两个入口：
- `complete(system, user)`：单轮问答，询问中心等场景使用
- `complete_chat(messages)`：完整 messages 数组，Agent 多轮对话使用
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
    client = _build_client()
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


async def complete_with_tools(
    messages: list[dict], tools: list[dict]
) -> object:
    """调用模型并允许它选择工具。

    Returns:
        OpenAI SDK 的 message 对象：
        - `message.content` 是文本回复
        - `message.tool_calls` 是模型想调用的工具列表

    调用方负责执行工具、把结果追加回 messages，再继续调用。
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
            response = await _build_client().chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
            )
            message = response.choices[0].message
            if not message.content and not message.tool_calls:
                raise ValueError("AI 返回了空回复")
            breaker.record_success()
            AI_CALLS.labels("success").inc()
            AI_CIRCUIT_OPEN.set(0)
            return message
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("ai.call_failed", attempt=attempt, error=repr(exc))
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(0.5)

    breaker.record_failure()
    AI_CALLS.labels("failure").inc()
    if breaker.current_state() == OPEN:
        AI_CIRCUIT_OPEN.set(1)
    raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from last_error


async def stream_chat(messages: list[dict]):
    """流式调用，逐段产出文本。

    注意：流一旦开始就无法重试；中途失败会抛 AppError，
    调用方需要把已经输出的内容保留下来或提示用户重试。
    """
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)

    if not breaker.allow_request():
        AI_CALLS.labels("circuit_open").inc()
        AI_CIRCUIT_OPEN.set(1)
        logger.warning("ai.circuit_open")
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    try:
        stream = await _build_client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            stream=True,
            temperature=0.7,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        breaker.record_success()
        AI_CALLS.labels("success").inc()
        AI_CIRCUIT_OPEN.set(0)
    except Exception as exc:  # noqa: BLE001
        breaker.record_failure()
        AI_CALLS.labels("failure").inc()
        logger.warning("ai.stream_failed", error=repr(exc))
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from exc
