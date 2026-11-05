"""业务层：模拟TA（数字分身）。

三条硬规则：
1. 必须明确告知这是基于历史数据的模拟，不是真人
2. 使用对方数据前必须对方授权，撤销即停用
3. 理想化模式不允许替对方做承诺
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.ai import client as ai_client
from app.modules.ai import retrieval
from app.modules.audit import service as audit_service
from app.modules.couples.models import Couple
from app.modules.simta import repository as repo
from app.modules.simta.schemas import ChatResponse, PersonaStateOut
from app.modules.users.models import User

DISCLAIMER = "这是基于历史数据模拟的 TA，不是本人。真实的想法，还是要问 TA。"

FAITHFUL_PROMPT = (
    "你正在扮演用户的伴侣。以下是 TA 在关系里留下的真实记录。\n"
    "要求：只基于这些记录说话；不确定的事情直接说不知道；"
    "不要编造 TA 没表达过的态度；语气像日常聊天，简短。"
)

IDEALIZED_PROMPT = (
    "你正在扮演用户理想中的伴侣版本，基于 TA 的历史记录做温和的延伸。\n"
    "要求：更耐心、更愿意倾听，可以给出情绪支持。\n"
    "绝对不要替 TA 做出承诺（例如「我永远爱你」「我一定会改」），"
    "也不要给出任何可以被当成真实约定的回答。"
)


def _partner_id(couple: Couple, user_id: int) -> int:
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def set_consent(
    session: AsyncSession, couple: Couple, user: User, authorized: bool
) -> None:
    await repo.upsert_consent(session, couple.id, user.id, authorized)
    if not authorized:
        await audit_service.record(
            session,
            user_id=user.id,
            couple_id=couple.id,
            action="simta.consent_revoke",
            target_type="persona_consent",
            target_id=user.id,
        )
    await session.commit()


async def set_fidelity(
    session: AsyncSession, couple: Couple, user: User, fidelity: str
) -> None:
    await repo.upsert_settings(session, couple.id, user.id, fidelity)
    await session.commit()


async def get_state(
    session: AsyncSession, couple: Couple, user: User
) -> PersonaStateOut:
    my_consent = await repo.get_consent(session, couple.id, user.id)
    partner_consent = await repo.get_consent(
        session, couple.id, _partner_id(couple, user.id)
    )
    settings = await repo.get_settings(session, couple.id, user.id)

    return PersonaStateOut(
        my_consent=bool(my_consent and my_consent.authorized),
        partner_consent=bool(partner_consent and partner_consent.authorized),
        fidelity=settings.fidelity if settings else "faithful",
    )


async def chat(
    session: AsyncSession, couple: Couple, user: User, message: str
) -> ChatResponse:
    target_id = _partner_id(couple, user.id)
    consent = await repo.get_consent(session, couple.id, target_id)
    if consent is None or not consent.authorized:
        raise AppError("对方还没有授权把 TA 的数据用于模拟", code=14001, status_code=403)

    settings = await repo.get_settings(session, couple.id, user.id)
    fidelity = settings.fidelity if settings else "faithful"

    fragments = await retrieval.collect_context(session, couple.id, target_id)
    context = "\n".join(fragments) if fragments else "（暂时没有可用的历史记录）"

    system = FAITHFUL_PROMPT if fidelity == "faithful" else IDEALIZED_PROMPT
    prompt = f"关于 TA 的记录：\n{context}\n\n用户说：{message}"

    try:
        reply = await ai_client.complete(system=system, user=prompt)
    except AppError as exc:
        if exc.code in (11001, 11003):
            # 降级：不把技术错误甩给用户
            raise AppError(
                "TA 的数字分身暂时连不上。真人一直在。",
                code=14002,
                status_code=503,
            ) from exc
        raise

    return ChatResponse(reply=reply, fidelity=fidelity, disclaimer=DISCLAIMER)
