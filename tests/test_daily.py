from app.modules.daily import service
from tests.helpers import seed_couple


async def test_today_returns_same_question_for_both(session):
    a, b, couple = await seed_couple(session)

    view_a = await service.today_view(session, couple, a)
    view_b = await service.today_view(session, couple, b)

    assert view_a.question == view_b.question
    assert view_a.my_answer is None


async def test_partner_answer_hidden_until_i_answer(session):
    a, b, couple = await seed_couple(session)
    await service.answer(session, couple, b, "今天被你逗笑了")

    before = await service.today_view(session, couple, a)
    assert before.my_answer is None
    assert before.partner_answer is None

    after = await service.answer(session, couple, a, "我也是")
    assert after.my_answer == "我也是"
    assert after.partner_answer == "今天被你逗笑了"


async def test_answer_can_be_updated(session):
    a, _, couple = await seed_couple(session)
    await service.answer(session, couple, a, "第一版")
    updated = await service.answer(session, couple, a, "改了")
    assert updated.my_answer == "改了"
