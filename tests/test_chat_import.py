"""聊天记录导入：解析容错、时间格式、双向授权、去重与画像统计。"""

import json

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.agent import import_service, importers, persona
from app.modules.agent.models import ChatMessage
from app.modules.ai import embeddings, indexing, vectorstore
from app.modules.simta import service as simta_service
from tests.helpers import seed_couple

JSONL = "\n".join(
    [
        '{"sender":"A","sent_at":"2024-05-01T20:00:00+08:00","content":"今天好累"}',
        '{"sender":"B","sent_at":"2024-05-01T20:01:00+08:00","content":"怎么啦"}',
        '{"sender":"A","sent_at":"2024-05-01T20:02:00+08:00","content":"老板又改需求"}',
        "not json",
        '{"sender":"C","sent_at":"2024-05-01T20:03:00+08:00","content":"陌生人"}',
    ]
)


def test_parse_jsonl_skips_bad_lines():
    result = importers.parse_messages(JSONL, "jsonl")

    assert len(result.messages) == 4
    assert result.skipped == 1
    assert result.messages[0].sent_at.tzinfo is not None


def test_parse_timestamp_formats():
    assert importers.parse_timestamp("2024-05-01 20:00:00").year == 2024
    assert importers.parse_timestamp("2024/05/01 20:00:00").year == 2024
    assert importers.parse_timestamp(1714564800).tzinfo is not None
    assert importers.parse_timestamp("2024-05-01T20:00:00+08:00").tzinfo is not None


async def test_import_requires_mutual_consent(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await import_service.import_chat_log(
            session,
            couple,
            a,
            filename="chat.jsonl",
            fmt="jsonl",
            raw=JSONL.encode(),
        )

    assert exc.value.code == 17002


async def test_import_maps_senders_and_dedupes(session):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, a, True)
    await simta_service.set_consent(session, couple, b, True)

    row = await import_service.import_chat_log(
        session,
        couple,
        a,
        filename="chat.jsonl",
        fmt="jsonl",
        raw=JSONL.encode(),
        owner_name="A",
        partner_name="B",
    )

    assert row.total_messages == 4
    assert row.imported_messages == 3
    # 一条坏行 + 一个对不上的人
    assert row.skipped_messages == 2

    count = await session.scalar(select(func.count()).select_from(ChatMessage))
    assert count == 3

    # 重复导入不会新增
    row2 = await import_service.import_chat_log(
        session,
        couple,
        a,
        filename="chat.jsonl",
        fmt="jsonl",
        raw=JSONL.encode(),
        owner_name="A",
        partner_name="B",
    )
    assert row2.imported_messages == 0

    count = await session.scalar(select(func.count()).select_from(ChatMessage))
    assert count == 3


async def test_import_rejects_one_sided_mapping(session):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, a, True)
    await simta_service.set_consent(session, couple, b, True)

    one_sided = "\n".join(
        [
            '{"sender":"A","sent_at":"2024-05-01T20:00:00+08:00","content":"只有我"}',
            '{"sender":"A","sent_at":"2024-05-01T20:01:00+08:00","content":"还是我"}',
        ]
    )

    with pytest.raises(AppError) as exc:
        await import_service.import_chat_log(
            session,
            couple,
            a,
            filename="chat.jsonl",
            fmt="jsonl",
            raw=one_sided.encode(),
            owner_name="A",
            partner_name="B",
        )

    assert exc.value.code == 17008


async def test_chat_windows_label_real_names_per_persona(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, a, True)
    await simta_service.set_consent(session, couple, b, True)
    import_row = await import_service.import_chat_log(
        session,
        couple,
        a,
        filename="chat.jsonl",
        fmt="jsonl",
        raw=JSONL.encode(),
        owner_name="A",
        partner_name="B",
    )

    captured: dict = {"documents": [], "metadatas": []}

    async def fake_embed(texts):
        return [[0.1] for _ in texts]

    async def fake_upsert(ids, vectors, documents, metadatas):
        captured["documents"].extend(documents)
        captured["metadatas"].extend(metadatas)

    async def fake_delete(ids):
        return None

    monkeypatch.setattr(embeddings, "is_configured", lambda: True)
    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(vectorstore, "upsert", fake_upsert)
    monkeypatch.setattr(vectorstore, "delete_ids", fake_delete)

    await indexing.index_chat_import(session, import_row.id)

    b_docs = [
        doc
        for doc, meta in zip(
            captured["documents"], captured["metadatas"], strict=True
        )
        if meta["user_id"] == b.id
    ]
    a_docs = [
        doc
        for doc, meta in zip(
            captured["documents"], captured["metadatas"], strict=True
        )
        if meta["user_id"] == a.id
    ]

    # B 的画像窗口里，B 的话标 B，A 的话标 A
    assert any("B：怎么啦" in doc for doc in b_docs)
    assert any("A：今天好累" in doc for doc in b_docs)
    # A 的画像窗口同理，不会把 B 的话标成 A
    assert any("A：老板又改需求" in doc for doc in a_docs)


async def test_persona_profile_uses_own_messages(session):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, a, True)
    await simta_service.set_consent(session, couple, b, True)
    await import_service.import_chat_log(
        session,
        couple,
        a,
        filename="chat.jsonl",
        fmt="jsonl",
        raw=JSONL.encode(),
        owner_name="A",
        partner_name="B",
    )

    profile = await persona.build_profile(session, couple.id, a.id)

    assert profile is not None
    assert profile.stats["messages"] == 2
    # 测试环境没有 LLM Key，风格描述应为空，但统计和样本仍生成
    assert profile.style_summary is None

    samples = json.loads(profile.samples_json or "[]")
    assert "今天好累" in samples
    assert "怎么啦" not in samples  # 对方的话不能进 A 的画像
