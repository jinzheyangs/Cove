"""争吵模式：伤害词提示、状态流转与复盘关闭。"""

import pytest

from app.core.errors import AppError
from app.modules.conflicts import service
from tests.helpers import seed_couple


async def test_start_creates_ongoing_session(session):
    _, _, couple = await seed_couple(session)
    conflict = await service.start(session, couple)
    assert conflict.status == "ongoing"


async def test_cannot_start_two_sessions(session):
    _, _, couple = await seed_couple(session)
    await service.start(session, couple)

    with pytest.raises(AppError) as exc:
        await service.start(session, couple)

    assert exc.value.code == 12001


async def test_attack_words_flagged_but_not_blocked(session):
    a, _, couple = await seed_couple(session)
    conflict = await service.start(session, couple)

    message, prompt = await service.send_message(
        session, couple, a, conflict.id, "你就是个废物"
    )

    assert message.flagged is True
    assert prompt is not None


async def test_normal_message_not_flagged(session):
    a, _, couple = await seed_couple(session)
    conflict = await service.start(session, couple)

    message, prompt = await service.send_message(
        session, couple, a, conflict.id, "我刚才有点难过"
    )

    assert message.flagged is False
    assert prompt is None


async def test_review_closes_only_after_both_submit(session):
    a, b, couple = await seed_couple(session)
    conflict = await service.start(session, couple)

    ended = await service.end(session, couple, conflict.id)
    assert ended.status == "reviewing"

    first = await service.submit_review(
        session, couple, a, conflict.id, "想被理解的是我的努力", "TA 需要被听见"
    )
    assert first.status == "reviewing"

    second = await service.submit_review(
        session, couple, b, conflict.id, "想被理解的是我的担心", "TA 需要被肯定"
    )
    assert second.status == "closed"
