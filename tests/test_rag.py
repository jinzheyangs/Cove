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

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]

    async def fake_upsert(ids, vectors, documents, metadatas) -> None:
        upserts.append(len(ids))

    async def fake_delete(ids) -> None:
        return None

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "upsert", fake_upsert)
    monkeypatch.setattr(vectorstore, "delete_ids", fake_delete)

    await indexing.index_diary(session, diary.id)

    assert upserts == [3]
    rows = list(
        await session.scalars(
            select(ChunkIndex).where(ChunkIndex.source_id == diary.id)
        )
    )
    assert len(rows) == 3
    assert all(row.user_id == a.id for row in rows)

    # 内容没变，第二次索引应该直接跳过
    await indexing.index_diary(session, diary.id)
    assert upserts == [3]


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
