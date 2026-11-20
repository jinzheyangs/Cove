"""模拟TA：授权与偏好状态。"""

from app.modules.simta import service
from tests.helpers import seed_couple


async def test_state_defaults_to_idealized_and_unauthorized(session):
    a, _, couple = await seed_couple(session)

    state = await service.get_state(session, couple, a)

    assert state.my_consent is False
    assert state.partner_consent is False
    assert state.fidelity == "idealized"


async def test_consent_roundtrip(session):
    a, b, couple = await seed_couple(session)

    await service.set_consent(session, couple, b, True)

    state = await service.get_state(session, couple, a)

    # a 看到的是「对方 b 已授权」「我自己没授权」
    assert state.partner_consent is True
    assert state.my_consent is False
