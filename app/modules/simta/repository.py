"""数据访问层：模拟TA 的授权与设置。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.simta.models import PersonaConsent, PersonaSettings


async def get_consent(
    session: AsyncSession, couple_id: int, user_id: int
) -> PersonaConsent | None:
    return await session.scalar(
        select(PersonaConsent).where(
            PersonaConsent.couple_id == couple_id, PersonaConsent.user_id == user_id
        )
    )


async def upsert_consent(
    session: AsyncSession, couple_id: int, user_id: int, authorized: bool
) -> PersonaConsent:
    consent = await get_consent(session, couple_id, user_id)
    if consent is None:
        consent = PersonaConsent(
            couple_id=couple_id, user_id=user_id, authorized=authorized
        )
        session.add(consent)
    else:
        consent.authorized = authorized
    await session.flush()
    return consent


async def get_settings(
    session: AsyncSession, couple_id: int, owner_id: int
) -> PersonaSettings | None:
    return await session.scalar(
        select(PersonaSettings).where(
            PersonaSettings.couple_id == couple_id, PersonaSettings.owner_id == owner_id
        )
    )


async def upsert_settings(
    session: AsyncSession, couple_id: int, owner_id: int, fidelity: str
) -> PersonaSettings:
    settings = await get_settings(session, couple_id, owner_id)
    if settings is None:
        settings = PersonaSettings(
            couple_id=couple_id, owner_id=owner_id, fidelity=fidelity
        )
        session.add(settings)
    else:
        settings.fidelity = fidelity
    await session.flush()
    return settings
