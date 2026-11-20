"""Chroma 向量库封装。

只做 HTTP 调用，不碰业务逻辑。
chromadb-client 是同步客户端，所有调用都放到线程池，避免阻塞事件循环。

关键约束：
- 每次查询都必须带 couple_id + user_id 过滤，否则会检索到别人（也就是你对象）的内容
- Chroma 只是索引，丢了可以从 PG 重建，不要把它当唯一数据源
"""

import asyncio
import threading

import structlog

from app.core.config import settings

logger = structlog.get_logger("vectorstore")

# 集合对象复用：以前每次查询都新建 HttpClient + get_or_create_collection，
# 一次对话要查两遍，光建连和元数据往返就吃掉一秒多。
# 现在第一次建好后一直复用；真连不上（容器重启之类）就丢掉重建一次。
_COLLECTION = None
_COLLECTION_LOCK = threading.Lock()


def _collection():
    """延迟创建集合。

    chromadb 是可选依赖，import 放在函数里，
    这样没装的时候只有调用向量检索才会报错。
    """
    global _COLLECTION
    if _COLLECTION is not None:
        return _COLLECTION

    with _COLLECTION_LOCK:
        if _COLLECTION is None:
            import chromadb

            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
            )
            _COLLECTION = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
    return _COLLECTION


def _reset_collection() -> None:
    """丢掉缓存的连接，下次调用重建。"""
    global _COLLECTION
    with _COLLECTION_LOCK:
        _COLLECTION = None


def _call(fn):
    """带着「连接过期就重建一次」的容错去跑一次同步调用。"""
    try:
        return fn(_collection())
    except Exception:
        _reset_collection()
        raise


def _call_retry(fn):
    """同上，但重建后再试一次：Chroma 短暂重启时能自己缓过来。"""
    try:
        return fn(_collection())
    except Exception:
        _reset_collection()
        return fn(_collection())



def warm() -> bool:
    """启动时预热：把集合先建好，第一句对话就不用等连接和元数据往返。

    失败不影响启动，后续调用会自己重建。
    """
    try:
        _collection()
        return True
    except Exception as exc:  # noqa: BLE001 - 预热失败不该拖垮启动
        logger.warning("vectorstore.warm_failed", error=repr(exc))
        _reset_collection()
        return False


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
        _call_retry(lambda c: c.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        ))

    await asyncio.to_thread(_run)


async def query(
    couple_id: int, user_id: int, embedding: list[float], top_k: int
) -> list[str]:
    """按相似度检索，只返回文档片段。

    过滤条件在服务端执行，返回的绝不会是其他关系或其他人的内容。
    """

    def _run() -> list[str]:
        result = _call_retry(lambda c: c.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=_where(couple_id, user_id),
        ))
        documents = result.get("documents") or []
        return documents[0] if documents else []

    return await asyncio.to_thread(_run)


async def delete_ids(ids: list[str]) -> None:
    """按向量 id 删除。用于重建某条业务数据的索引。"""
    if not ids:
        return

    def _run() -> None:
        _call_retry(lambda c: c.delete(ids=ids))

    await asyncio.to_thread(_run)


async def existing_ids(ids: list[str]) -> set[str]:
    """返回这批 id 里 Chroma 实际还留着的那些。

    PG 的 chunk_index 只是「我索引过」的记录，Chroma 可能因为容器重建、
    卷丢数据、别处误删而少掉一部分。重建索引前用它核对一次，
    否则 content_hash 没变就会一直被跳过，向量永久缺。
    """
    if not ids:
        return set()

    def _run() -> set[str]:
        result = _call(lambda c: c.get(ids=list(ids), include=[]))
        return set(result.get("ids") or [])

    try:
        return await asyncio.to_thread(_run)
    except Exception as exc:  # noqa: BLE001 - 核对失败就当成缺失，让调用方重建
        logger.warning("vectorstore.existing_ids_failed", error=repr(exc))
        return set()


async def all_ids() -> set[str]:
    """列出集合里的全部向量 id。

    对账用：chunk_index 里没有的一律视为孤儿，清掉。
    失败返回空集合，让调用方跳过清理而不是误删。
    """

    def _run() -> set[str]:
        result = _call(lambda c: c.get(include=[]))
        return set(result.get("ids") or [])

    try:
        return await asyncio.to_thread(_run)
    except Exception as exc:  # noqa: BLE001 - 查询失败就不清理孤儿
        logger.warning("vectorstore.all_ids_failed", error=repr(exc))
        return set()


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
        _call_retry(lambda c: c.delete(where=where))

    await asyncio.to_thread(_run)
