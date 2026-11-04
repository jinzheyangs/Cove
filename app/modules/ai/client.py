"""大模型调用出口。

所有 AI 请求只能从这里出去，方便统一加超时、重试和日志。
没有配置 Key 时直接报错，而不是静默返回假内容。
"""

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError


def _build_client() -> AsyncOpenAI:
    if not settings.LLM_API_KEY:
        raise AppError("AI 服务尚未配置", code=11001, status_code=503)
    return AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=30.0,
    )


async def complete(*, system: str, user: str) -> str:
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
        raise AppError("AI 没有返回内容", code=11002, status_code=502)
    return content
