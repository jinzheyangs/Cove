"""业务层：情侣绑定与解绑规则。"""

import secrets
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import today
from app.modules.agent.models import ChatMemory
from app.modules.ai import indexing
from app.modules.anniversaries.models import Anniversary
from app.modules.audit import service as audit_service
from app.modules.bills.models import Bill
from app.modules.coins import service as coins_service
from app.modules.coins.models import CoinAccount
from app.modules.couples import repository as repo
from app.modules.couples.models import Couple, CoupleInvite
from app.modules.couples.schemas import UsStatsOut
from app.modules.diaries.models import Diary
from app.modules.notifications import service as notification_service
from app.modules.secrets.models import Secret
from app.modules.todos.models import TodoItem
from app.modules.users import repository as user_repo
from app.modules.users.models import User

# 去掉了容易混淆的 0/O/I/1，方便口头或截图传递
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

logger = structlog.get_logger("couples")
_INVITE_TTL = timedelta(hours=24)

# 新绑定的两个人各发这么多金币。
# 不发的话双方都是 0：谁都批不了对方的金币申请，
# 商城和秘密树也都用不了 —— 一进来就是个死锁。
WELCOME_COINS = 30


def _generate_code() -> str:
    """生成 6 位邀请码。

    6 位、32 个字符 ≈ 10 亿种组合，对两个人使用完全足够。
    用 secrets 而不是 random：邀请码是权限凭证，不能被预测。
    """
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def create_invite(session: AsyncSession, user: User) -> CoupleInvite:
    """生成邀请码。

    已经绑定的人不能再生成。
    理论上邀请码可能碰撞，靠唯一索引兜底，冲突时换一个重试。
    """
    if await repo.get_active_by_user(session, user.id) is not None:
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)

    # 邀请码理论上可能碰撞，重试几次
    for _ in range(5):
        try:
            invite = await repo.create_invite(
                session,
                inviter_id=user.id,
                code=_generate_code(),
                expires_at=datetime.now(UTC) + _INVITE_TTL,
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue

        await session.refresh(invite)
        return invite

    raise AppError("邀请码生成失败，请重试", code=2002, status_code=500)


async def bind(session: AsyncSession, user: User, code: str) -> Couple:
    """用邀请码绑定两个人。

    并发安全的关键：
    1. 先按 user_id 升序锁住双方用户行，把并发绑定串行化
    2. 锁内再检查双方是否已有 active 关系
    3. 数据库的部分唯一索引做最后兜底

    通知和审计与关系创建在同一个事务里提交，
    不会出现“绑定了但没通知”或“通知了但回滚了”。
    """
    invite = await repo.get_active_invite_by_code(session, code.strip().upper())
    if invite is None:
        raise AppError("邀请码无效", code=2003, status_code=404)
    if invite.expires_at <= datetime.now(UTC):
        raise AppError("邀请码已过期", code=2004, status_code=410)
    if invite.inviter_id == user.id:
        raise AppError("不能绑定自己", code=2005, status_code=400)

    # 排序后加锁，避免两个并发请求以相反顺序加锁造成死锁
    ids = sorted({invite.inviter_id, user.id})
    await repo.lock_users(session, ids)

    # 拿到锁之后重新检查，防止检查与写入之间被别人插队
    if await repo.get_active_by_user(session, user.id) is not None:
        await session.rollback()
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)
    if await repo.get_active_by_user(session, invite.inviter_id) is not None:
        await session.rollback()
        raise AppError("对方已经绑定过伴侣了", code=2006, status_code=409)

    couple = await repo.create_couple(
        session,
        # ids 已排序，保证 user1_id < user2_id 的约束成立
        user1_id=ids[0],
        user2_id=ids[1],
        bind_at=datetime.now(UTC),
        # 关系是拿邀请码建起来的，发起人是邀请码的持有者
        created_by=invite.inviter_id,
    )
    invite.status = "used"

    # 见面礼：两个人各一笔初始金币。
    # 和关系创建在同一个事务里，绑定失败就一起回滚，不会留下半截。
    # 幂等键按「couple + 人」生成，重复绑定（解绑后重新配对）也只有各自一次。
    for uid in ids:
        await coins_service.mint_locked(
            session,
            couple_id=couple.id,
            actor_id=user.id,
            recipient_id=uid,
            amount=WELCOME_COINS,
            tx_type="reward",
            ref_type="couple",
            ref_id=couple.id,
            remark="新情侣见面礼",
            idempotency_key=f"welcome:{couple.id}:{uid}",
        )

    await notification_service.notify(
        session,
        user_id=invite.inviter_id,
        type="couple.bound",
        title="你们已经绑定啦",
        related_type="couple",
        related_id=couple.id,
    )
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="couple.bind",
        target_type="couple",
        target_id=couple.id,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        # 极端并发下唯一索引兜底
        await session.rollback()
        raise AppError("绑定失败，请重试", code=2007, status_code=409) from exc

    await session.refresh(couple)
    return couple


async def get_active_couple(session: AsyncSession, user_id: int) -> Couple | None:
    """查询当前生效的关系，没有则返回 None（不是错误）。"""
    return await repo.get_active_by_user(session, user_id)


async def us_stats(session: AsyncSession, couple: Couple, user: User) -> UsStatsOut:
    """解绑前那张「你们攒下了什么」：只数数量，不改任何东西。

    统计口径按「这段关系」算（所有表和 couple 挂钩），
    所以解绑之后重新绑定，会看到新的一段从零开始。
    """

    async def _count(model, *where) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.couple_id == couple.id, *where)
            )
            or 0
        )

    coins = int(
        await session.scalar(
            select(func.coalesce(func.sum(CoinAccount.balance), 0)).where(
                CoinAccount.user_id.in_([couple.user1_id, couple.user2_id])
            )
        )
        or 0
    )

    # 起始日没填就退回绑定那天：解绑提示里不该出现空着的「在一起」天数
    since = couple.start_date or couple.bind_at.date()
    # 和首页「第 N 天」同一口径：在一起当天就算第 1 天，别跟首页差一天
    days = max(0, (today() - since).days) + 1

    partner_id = couple.user2_id if couple.user1_id == user.id else couple.user1_id
    partner = await session.get(User, partner_id)

    return UsStatsOut(
        days_together=days,
        since=since,
        diaries=await _count(Diary),
        secrets=await _count(Secret),
        todos_pending=await _count(TodoItem, TodoItem.status == "pending"),
        todos_done=await _count(TodoItem, TodoItem.status == "completed"),
        bills=await _count(Bill),
        anniversaries=await _count(Anniversary),
        coins=coins,
        partner_nickname=partner.nickname if partner else None,
    )


async def update_start_date(
    session: AsyncSession, couple: Couple, start_date: date | None
) -> Couple:
    """写入「在一起」的起始日。

    允许传 None 清空（清空后纪念日退回使用 bind_at 的日期）。
    日期不能是未来，校验在 schema 层做。
    """
    couple.start_date = start_date
    await session.commit()
    await session.refresh(couple)
    return couple


async def unbind(
    session: AsyncSession,
    couple: Couple,
    user: User,
    confirm: bool,
    reason: str | None = None,
) -> Couple:
    """解除绑定。

    产品规则：解绑后双方都要回到登录页，因此这里会：
    1. 改关系状态（不删业务数据，日记/秘密/账目仍保留）
    2. 吊销双方所有 refresh token，双方都无法静默续期
    3. 给对方发一条解绑通知，前端守卫据此/在轮询发现后退回登录页
    4. 清掉这段关系在向量库里的索引和对话记忆

    第 4 步只删「索引」和「对话记忆块」：日记、账目这些原文都在 PG 里，
    不受影响；重新绑定会建新的 couple，检索从零开始，
    不会捞到上一段关系的记忆。
    """
    if not confirm:
        raise AppError("请确认解除绑定", code=2008, status_code=400)

    now = datetime.now(UTC)
    couple.status = "unbound"
    couple.unbound_at = now

    # 双方的刷新令牌全部吊销，强制重新登录
    await user_repo.revoke_all_refresh_tokens(session, couple.user1_id, now)
    await user_repo.revoke_all_refresh_tokens(session, couple.user2_id, now)

    # 通知被解绑的另一方（不是当前操作的人）
    partner_id = (
        couple.user2_id if user.id == couple.user1_id else couple.user1_id
    )
    await notification_service.notify(
        session,
        user_id=partner_id,
        type="couple.unbound",
        title="你们已经解除绑定",
        related_type="couple",
        related_id=couple.id,
    )

    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="couple.unbind",
        target_type="couple",
        target_id=couple.id,
        detail={"reason": reason} if reason else None,
    )
    await session.commit()

    # 清掉这段关系的向量索引和对话记忆。
    # 放在主事务提交之后：清理失败只丢索引（可从 PG 重建），
    # 不会把「已经解绑成功」这件事一起回滚。
    try:
        for uid in (couple.user1_id, couple.user2_id):
            await indexing.delete_user_vectors(session, couple.id, uid)
        await session.execute(
            delete(ChatMemory).where(ChatMemory.couple_id == couple.id)
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001 - 清理失败不能影响解绑结果
        await session.rollback()
        logger.warning(
            "couples.unbind_cleanup_failed",
            couple_id=couple.id,
            error=repr(exc),
        )

    await session.refresh(couple)
    return couple
