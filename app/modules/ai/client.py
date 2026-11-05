"""大模型调用出口。

所有 AI 请求只能从这里出去，统一做超时、重试、熔断、指标和日志。

边界：
- 没配置 Key：明确报错（11001），不静默返回假内容
- 熔断打开：直接拒绝（11003），不发请求
- 单次失败：重试一次
- 连续失败：打开熔断，保护上游和钱包
"""

import asyncio

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError
from app.core.metrics import AI_CALLS, AI_CIRCUIT_OPEN
from app.modules.ai.breaker import OPEN, CircuitBreaker

logger = structlog.get_logger("ai")

# 进程级单例。配置来自环境变量，启动后不会变
breaker = CircuitBreaker(
    failure_threshold=settings.AI_FAILURE_THRESHOLD,
    recovery_timeout=settings.AI_RECOVERY_SECONDS,
)

# 总共尝试 2 次：首次 + 1 次重试
_MAX_ATTEMPTS = 2


def _build_client() -> AsyncOpenAI:
    """每次调用新建客户端。

    OpenAI SDK 的客户端很轻，内部复用 httpx 连接池；
    这里新建主要是为了拿到最新的配置和独立超时。
    """
    return AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=30.0,
    )


async def _call(system: str, user: str) -> str:
    """真正发起一次模型调用。

    空内容当失败处理：有些供应商会在限流时返回空 choices。
    """
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
    """调用模型并返回文本。

    Raises:
        AppError(11001): 未配置 LLM_API_KEY
        AppError(11003): 熔断打开，或重试后仍失败

    调用方（询问中心 / 模拟TA）会把 11001/11003 转成各自的降级文案。
    """
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)

    # 熔断打开：连请求都不发
    if not breaker.allow_request():
        AI_CALLS.labels("circuit_open").inc()
        AI_CIRCUIT_OPEN.set(1)
        logger.warning("ai.circuit_open")
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            reply = await _call(system, user)
            breaker.record_success()
            AI_CALLS.labels("success").inc()
            AI_CIRCUIT_OPEN.set(0)
            return reply
        except Exception as exc:  # noqa: BLE001 - 外部依赖，任何失败都重试一次
            last_error = exc
            logger.warning("ai.call_failed", attempt=attempt, error=repr(exc))
            if attempt < _MAX_ATTEMPTS:
                # 固定 0.5 秒退避。外部依赖通常几秒内恢复，
                # 这里不需要复杂的指数退避
                await asyncio.sleep(0.5)

    # 两次都失败：记一次熔断失败
    breaker.record_failure()
    AI_CALLS.labels("failure").inc()
    if breaker.current_state() == OPEN:
        AI_CIRCUIT_OPEN.set(1)
    logger.error("ai.unavailable", attempts=_MAX_ATTEMPTS)
    raise AppError("AI 服务暂时不可用", code=11003, status_code=503) from last_error
