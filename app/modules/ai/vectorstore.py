"""Chroma 向量库封装。

只做 HTTP 调用，不碰业务逻辑。
chromadb-client 是同步客户端，所有调用都放到线程池，避免阻塞事件循环。

关键约束：
- 每次查询都必须带 couple_id + user_id 过滤，否则会检索到别人（也就是你对象）的内容
- Chroma 只是索引，丢了可以从 PG 重建，不要把它当唯一数据源
"""

import asyncio

import structlog

from app.core.config import settings

logger = structlog.get_logger("vectorstore")


def _collection():
    """延迟创建集合。

    chromadb 是可选依赖，import 放在函数里，
    这样没装的时候只有调用向量检索才会报错。
    """
    import chromadb

    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _where(couple_id: int, user_id: int) -> dict:
    """组合过滤条件。两个条件必须同时满足。"""
    return {"$and": [{"couple_id": couple_id}, {"user_id": user_id}]}


async def upsert(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """写入或覆盖一批向量。"""

    def _run() -> None:
        _collection().upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    await asyncio.to_thread(_run)


async def query(
    couple_id: int, user_id: int, embedding: list[float], top_k: int
) -> list[str]:
    """按相似度检索，只返回文档片段。

    过滤条件在服务端执行，返回的绝不会是其他关系或其他人的内容。
    """

    def _run() -> list[str]:
        result = _collection().query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=_where(couple_id, user_id),
        )
        documents = result.get("documents") or []
        return documents[0] if documents else []

    return await asyncio.to_thread(_run)


async def delete_ids(ids: list[str]) -> None:
    """按向量 id 删除。用于重建某条业务数据的索引。"""
    if not ids:
        return

    def _run() -> None:
        _collection().delete(ids=ids)

    await asyncio.to_thread(_run)


async def delete_for_user(couple_id: int | None, user_id: int) -> None:
    """删除某个用户的全部向量。

    couple_id 为空时按用户全局删除（注销账号场景）；
    否则只删当前关系内的（撤销模拟TA 授权场景）。
    """

    if couple_id is None:
        where: dict = {"user_id": user_id}
    else:
        where = _where(couple_id, user_id)

    def _run() -> None:
        _collection().delete(where=where)

    await asyncio.to_thread(_run)
