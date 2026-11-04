import pytest

from app.core.errors import AppError
from app.modules.ai import client as ai_client
from app.modules.inquiries import service
from tests.helpers import seed_couple


async def test_inputs_hidden_until_both_submitted(session):
    a, b, couple = await seed_couple(session)
    item = await service.create(session, couple, "周末去哪")

    await service.submit_input(session, couple, a, item.id, "我想去爬山")

    detail = await service.get_detail(session, couple, a, item.id)
    assert detail.my_input_submitted is True
    assert detail.submitted_count == 1
    assert detail.inputs == []

    await service.submit_input(session, couple, b, item.id, "我想在家躺着")

    detail = await service.get_detail(session, couple, a, item.id)
    assert detail.inputs == ["我想去爬山", "我想在家躺着"]


async def test_generate_requires_both_inputs(session):
    a, _, couple = await seed_couple(session)
    item = await service.create(session, couple, "要不要养猫")
    await service.submit_input(session, couple, a, item.id, "想养")

    with pytest.raises(AppError) as exc:
        await service.generate(session, couple, item.id)

    assert exc.value.code == 13003


async def test_generate_calls_ai_once(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    item = await service.create(session, couple, "要不要养猫")
    await service.submit_input(session, couple, a, item.id, "想养")
    await service.submit_input(session, couple, b, item.id, "担心太麻烦")

    calls = []

    async def fake_complete(*, system: str, user: str) -> str:
        calls.append((system, user))
        return "可以先试养一周，再一起决定"

    monkeypatch.setattr(ai_client, "complete", fake_complete)

    result = await service.generate(session, couple, item.id)

    assert result.status == "reviewing"
    assert result.ai_response == "可以先试养一周，再一起决定"
    assert len(calls) == 1
    assert "想养" in calls[0][1]
    assert "担心太麻烦" in calls[0][1]


async def test_supplement_after_ai_then_close(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    item = await service.create(session, couple, "q")
    await service.submit_input(session, couple, a, item.id, "a")
    await service.submit_input(session, couple, b, item.id, "b")

    async def fake_complete(*, system: str, user: str) -> str:
        return "建议"

    monkeypatch.setattr(ai_client, "complete", fake_complete)
    await service.generate(session, couple, item.id)

    await service.supplement(session, couple, a, item.id, "我同意这个方案")
    closed = await service.close(session, couple, item.id)

    assert closed.status == "closed"
    detail = await service.get_detail(session, couple, a, item.id)
    assert detail.supplements == ["我同意这个方案"]
