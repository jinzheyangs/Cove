"""Embedding 客户端。

走 OpenAI 兼容接口，供应商可替换：
通义、智谱、硅基流动、本地 vLLM 都支持这个协议。

没配置时 `is_configured()` 返回 False，
检索层会自动退回到「最近记录」模式，而不是报错。
"""

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.errors import AppError

logger = structlog.get_logger("embeddings")


def is_configured() -> bool:
    """是否配置了 embedding。三个关键项缺一不可。"""
    return bool(
        settings.RAG_ENABLED
        and settings.EMBEDDING_API_KEY
        and settings.EMBEDDING_MODEL
    )


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL or None,
        timeout=30.0,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """把一批文本转成向量。

    批量调用比逐条调用便宜也快；调用方负责控制批量大小。
    """
    if not is_configured():
        raise AppError("embedding 尚未配置", code=11004, status_code=503)

    kwargs: dict = {"model": settings.EMBEDDING_MODEL, "input": texts}
    if settings.EMBEDDING_DIMENSIONS:
        kwargs["dimensions"] = settings.EMBEDDING_DIMENSIONS

    response = await _client().embeddings.create(**kwargs)
    # 按 index 排序，防止供应商返回乱序
    items = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in items]


async def embed_one(text: str) -> list[float]:
    """单条文本向量化，供查询时使用。"""
    vectors = await embed_texts([text])
    return vectors[0]
