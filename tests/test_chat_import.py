"""聊天记录导入：解析容错、时间格式、双向授权、去重与画像统计。"""

import json

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.agent import import_service, importers, persona
from app.modules.agent.models import ChatMessage
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
