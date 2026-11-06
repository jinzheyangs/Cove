"""业务层：模拟TA（数字分身）。

三条硬规则：
1. 必须明确告知这是基于历史数据的模拟，不是真人
2. 使用对方数据前必须对方授权，撤销即停用
3. 理想化模式不允许替对方做承诺
"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.queue import enqueue
from app.modules.agent.models import PersonaProfile
from app.modules.ai import client as ai_client
from app.modules.ai import retrieval
from app.modules.audit import service as audit_service
from app.modules.couples.models import Couple
from app.modules.simta import repository as repo
from app.modules.simta.schemas import ChatResponse, PersonaStateOut
from app.modules.users.models import User

# 每次回复都必须带上，前端应固定展示在消息旁边
DISCLAIMER = "这是基于历史数据模拟的 TA，不是本人。真实的想法，还是要问 TA。"

# 忠实模式：只依据已知记录，不脑补
FAITHFUL_PROMPT = (
    "你正在扮演用户的伴侣。以下是 TA 在关系里留下的真实记录。\n"
    "要求：只基于这些记录说话；不确定的事情直接说不知道；"
    "不要编造 TA 没表达过的态度；语气像日常聊天，简短。"
)

# 理想化模式：允许更温柔，但绝对不能替真人许下承诺
IDEALIZED_PROMPT = (
    "你正在扮演用户理想中的伴侣版本，基于 TA 的历史记录做温和的延伸。\n"
    "要求：更耐心、更愿意倾听，可以给出情绪支持。\n"
    "绝对不要替 TA 做出承诺（例如「我永远爱你」「我一定会改」），"
    "也不要给出任何可以被当成真实约定的回答。"
)

_AI_UNAVAILABLE = (11001, 11003)


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人，也就是被模拟的对象。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def set_consent(
    session: AsyncSession, couple: Couple, user: User, authorized: bool
) -> None:
    """开启或撤销授权。

    撤销会写审计日志：这是敏感操作，必须留痕。
    """
    await repo.upsert_consent(session, couple.id, user.id, authorized)
    if not authorized:
        # 撤销即停用：派生的风格画像也一并删除，不能只删向量。
        # 原始聊天记录保留（双方共同导入，删掉会连带对方的数据）。
        await session.execute(
            delete(PersonaProfile).where(
                PersonaProfile.couple_id == couple.id,
                PersonaProfile.user_id == user.id,
            )
        )
        await audit_service.record(
            session,
            user_id=user.id,
            couple_id=couple.id,
            action="simta.consent_revoke",
            target_type="persona_consent",
            target_id=user.id,
        )
    await session.commit()

    # 撤销授权后必须把已经索引的向量删掉，否则数据还留在向量库里
    if not authorized:
        await enqueue("delete_user_vectors", couple.id, user.id)


async def set_fidelity(
    session: AsyncSession, couple: Couple, user: User, fidelity: str
) -> None:
    """切换忠实度偏好。"""
    await repo.upsert_settings(session, couple.id, user.id, fidelity)
    await session.commit()


async def get_state(
    session: AsyncSession, couple: Couple, user: User
) -> PersonaStateOut:
    """返回当前的授权与偏好状态。"""
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
    """和对方的分身对话。

    流程：
    1. 检查对方是否授权（未授权直接 403）
    2. 读取自己的忠实度偏好
    3. 从数据库检索对方的历史记录（日记）
    4. 拼 system prompt，调用一次模型
    5. AI 不可用时返回温和提示，而不是技术错误
    """
    target_id = _partner_id(couple, user.id)
    consent = await repo.get_consent(session, couple.id, target_id)
    if consent is None or not consent.authorized:
        raise AppError("对方还没有授权把 TA 的数据用于模拟", code=14001, status_code=403)

    settings = await repo.get_settings(session, couple.id, user.id)
    fidelity = settings.fidelity if settings else "faithful"

    # 传当前问题，检索层会优先走向量相似度；未配置时自动退回最近记录
    fragments = await retrieval.collect_context(
        session, couple.id, target_id, query_text=message
    )
    context = "\n".join(fragments) if fragments else "（暂时没有可用的历史记录）"

    system = FAITHFUL_PROMPT if fidelity == "faithful" else IDEALIZED_PROMPT
    prompt = f"关于 TA 的记录：\n{context}\n\n用户说：{message}"

    try:
        reply = await ai_client.complete(system=system, user=prompt)
    except AppError as exc:
        if exc.code in _AI_UNAVAILABLE:
            # 降级：不把技术错误甩给用户
            raise AppError(
                "TA 的数字分身暂时连不上。真人一直在。",
                code=14002,
                status_code=503,
            ) from exc
        raise

    return ChatResponse(reply=reply, fidelity=fidelity, disclaimer=DISCLAIMER)
