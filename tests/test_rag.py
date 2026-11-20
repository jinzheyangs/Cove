"""RAG：切片、检索降级、向量过滤、索引构建与增量跳过。"""

from sqlalchemy import select

from app.core.config import settings
from app.modules.ai import embeddings, indexing, retrieval, vectorstore
from app.modules.ai.models import ChunkIndex
from app.modules.diaries import service as diary_service
from app.modules.diaries.schemas import DiaryCreate
from tests.helpers import seed_couple


def test_chunk_text_short_text_is_one_chunk():
    assert indexing.chunk_text("你好", 400, 50) == ["你好"]


def test_chunk_text_overlaps():
    text = "".join(str(i % 10) for i in range(1000))

    chunks = indexing.chunk_text(text, 400, 50)

    assert len(chunks) == 3
    assert len(chunks[0]) == 400
    # 第二段从第一段的第 350 个字符开始，重叠 50 个字符
    assert chunks[1][:50] == chunks[0][-50:]


def test_chunk_text_empty_returns_nothing():
    assert indexing.chunk_text("   \n ", 400, 50) == []


async def test_retrieval_falls_back_when_not_configured(session, monkeypatch):
    _, b, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "")
    await diary_service.create(
        session, couple, b, DiaryCreate(content="最近工作很累，想被抱一下")
    )

    docs = await retrieval.collect_context(session, couple.id, b.id, "今天怎么样")

    assert any("最近工作很累" in doc for doc in docs)


async def test_rag_uses_couple_and_user_filters(session, monkeypatch):
    _, b, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "test")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-model")

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    captured: dict = {}

    async def fake_query(couple_id, user_id, embedding, top_k):
        captured.update(couple_id=couple_id, user_id=user_id, top_k=top_k)
        return ["相关片段"]

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "query", fake_query)

    docs = await retrieval.collect_context(session, couple.id, b.id, "问题")

    assert docs == ["相关片段"]
    assert captured == {
        "couple_id": couple.id,
        "user_id": b.id,
        "top_k": settings.RAG_TOP_K,
    }


async def test_index_diary_creates_chunks_and_skips_unchanged(session, monkeypatch):
    a, _, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "test")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-model")
    monkeypatch.setattr(settings, "RAG_CHUNK_SIZE", 100)
    monkeypatch.setattr(settings, "RAG_CHUNK_OVERLAP", 10)

    diary = await diary_service.create(
        session, couple, a, DiaryCreate(content="x" * 250)
    )

    upserts: list[int] = []
    present: set[str] = set()

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]

    async def fake_upsert(ids, vectors, documents, metadatas) -> None:
        upserts.append(len(ids))
        present.update(ids)

    async def fake_delete(ids) -> None:
        for one in ids:
            present.discard(one)

    async def fake_existing(ids) -> set[str]:
        return {one for one in ids if one in present}

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "upsert", fake_upsert)
    monkeypatch.setattr(vectorstore, "delete_ids", fake_delete)
    monkeypatch.setattr(vectorstore, "existing_ids", fake_existing)

    await indexing.index_diary(session, diary.id)

    assert upserts == [3]
    rows = list(
        await session.scalars(
            select(ChunkIndex).where(ChunkIndex.source_id == diary.id)
        )
    )
    assert len(rows) == 3
    assert all(row.user_id == a.id for row in rows)

    # 内容没变、向量也都在，第二次索引应该直接跳过
    await indexing.index_diary(session, diary.id)
    assert upserts == [3]

    # Chroma 那边丢了向量（容器重建、卷丢数据）时必须重建，不能一直跳过
    present.clear()
    await indexing.index_diary(session, diary.id)
    assert upserts == [3, 3]


async def test_delete_diary_vectors_removes_mapping(session, monkeypatch):
    a, _, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "test")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-model")

    diary = await diary_service.create(session, couple, a, DiaryCreate(content="要删除的"))

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]

    async def fake_upsert(*args, **kwargs) -> None:
        return None

    deleted: list[list[str]] = []

    async def fake_delete(ids) -> None:
        deleted.append(ids)

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "upsert", fake_upsert)
    monkeypatch.setattr(vectorstore, "delete_ids", fake_delete)

    await indexing.index_diary(session, diary.id)
    await indexing.delete_diary_vectors(session, diary.id)

    rows = list(
        await session.scalars(
            select(ChunkIndex).where(ChunkIndex.source_id == diary.id)
        )
    )
    assert rows == []
    assert deleted  # 确认调用过向量删除


async def test_reconcile_vectors_repairs_missing_and_removes_orphans(session, monkeypatch):
    """对账任务：Chroma 丢的补回来，PG 没记录的孤儿删掉。"""
    a, _, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "test")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-model")
    monkeypatch.setattr(settings, "RAG_CHUNK_SIZE", 100)
    monkeypatch.setattr(settings, "RAG_CHUNK_OVERLAP", 10)

    diary = await diary_service.create(
        session, couple, a, DiaryCreate(content="一起去看了海")
    )

    present: set[str] = set()
    deleted: list[list[str]] = []

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]

    async def fake_upsert(ids, vectors, documents, metadatas) -> None:
        present.update(ids)

    async def fake_delete(ids) -> None:
        deleted.append(list(ids))
        for one in ids:
            present.discard(one)

    async def fake_existing(ids) -> set[str]:
        return {one for one in ids if one in present}

    async def fake_all() -> set[str]:
        return set(present) | {"diary:999:0"}

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "upsert", fake_upsert)
    monkeypatch.setattr(vectorstore, "delete_ids", fake_delete)
    monkeypatch.setattr(vectorstore, "existing_ids", fake_existing)
    monkeypatch.setattr(vectorstore, "all_ids", fake_all)

    await indexing.index_diary(session, diary.id)
    expected = {f"diary:{diary.id}:0"}
    assert expected <= present

    # 模拟 Chroma 把这条弄丢了
    present.clear()
    stats = await indexing.reconcile_vectors(session)

    assert stats["repaired"] == 1
    assert expected <= present
    # PG 里没有记录的向量 id 当孤儿删掉
    assert any("diary:999:0" in batch for batch in deleted)

