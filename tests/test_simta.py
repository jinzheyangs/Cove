import pytest

from app.core.errors import AppError
from app.modules.ai import client as ai_client
from app.modules.diaries import service as diary_service
from app.modules.diaries.schemas import DiaryCreate
from app.modules.simta import service
from tests.helpers import seed_couple


async def test_chat_requires_partner_consent(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await service.chat(session, couple, a, "在吗")

    assert exc.value.code == 14001


async def test_chat_uses_partner_diary_as_context(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await diary_service.create(
        session, couple, b, DiaryCreate(content="最近工作很累，想被抱一下")
    )
    await service.set_consent(session, couple, b, True)

    captured = {}

    async def fake_complete(*, system: str, user: str) -> str:
        captured["system"] = system
        captured["user"] = user
        return "我在，抱一下。"

    monkeypatch.setattr(ai_client, "complete", fake_complete)

    result = await service.chat(session, couple, a, "今天怎么样")

    assert result.reply == "我在，抱一下。"
    assert result.disclaimer
    assert "最近工作很累" in captured["user"]


async def test_idealized_mode_forbids_promises(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await service.set_consent(session, couple, b, True)
    await service.set_fidelity(session, couple, a, "idealized")

    captured = {}

    async def fake_complete(*, system: str, user: str) -> str:
        captured["system"] = system
        return "嗯"

    monkeypatch.setattr(ai_client, "complete", fake_complete)
    await service.chat(session, couple, a, "你会一直陪着我吗")

    assert "理想" in captured["system"]
    assert "不要替 TA 做出承诺" in captured["system"]


async def test_revoking_consent_blocks_chat(session):
    a, b, couple = await seed_couple(session)
    await service.set_consent(session, couple, b, True)
    await service.set_consent(session, couple, b, False)

    with pytest.raises(AppError) as exc:
        await service.chat(session, couple, a, "在吗")

    assert exc.value.code == 14001
