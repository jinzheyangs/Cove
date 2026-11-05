"""大模型调用出口。

所有 AI 请求只能从这里出去，统一做超时、重试、熔断和日志。
没有配置 Key 时直接报错，而不是静默返回假内容。
"""

import asyncio

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError
from app.core.metrics import AI_CALLS
from app.modules.ai.breaker import CircuitBreaker

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


async def _call(system: str, user: str) -> str:
    client = _build_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI 返回了空内容")
    return content


async def complete(*, system: str, user: str) -> str:
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)

    if not breaker.allow_request():
        AI_CALLS.labels("circuit_open").inc()
        logger.warning("ai.circuit_open")
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            reply = await _call(system, user)
            breaker.record_success()
            AI_CALLS.labels("success").inc()
            return reply
        except Exception as exc:  # noqa: BLE001 - 外部依赖，任何失败都重试一次
            last_error = exc
            logger.warning("ai.call_failed", attempt=attempt, error=repr(exc))
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(0.5)

    breaker.record_failure()
    AI_CALLS.labels("failure").inc()
    logger.error("ai.unavailable", attempts=_MAX_ATTEMPTS)
    raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from last_error
