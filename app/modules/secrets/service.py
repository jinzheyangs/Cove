"""业务层：秘密的发布、摘取、燃尽与销毁。

摘取是这里最关键的操作：
「扣金币」和「标记已读/燃尽」必须在同一个事务里，
否则会出现扣了钱但秘密没标记、或者秘密没了但没扣钱。
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.notifications import service as notification_service
from app.modules.secrets import repository as repo
from app.modules.secrets.models import Secret
from app.modules.secrets.schemas import DEFAULT_COST, SecretCreate, SecretDetail, SecretListItem
from app.modules.users.models import User

# 阅后即焚的燃尽期：内容先保留这么久，之后由后台任务清空。
# 留出缓冲是为了应对“响应丢失”：客户端还没看到就删掉会永久丢失。
BURN_GRACE = timedelta(hours=24)


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def publish(
    session: AsyncSession, couple: Couple, author: User, body: SecretCreate
) -> Secret:
    """发布一条秘密。

    价格不填时按等级取默认值：
    normal 10 币，deep 30 币。
    """
    cost = body.cost_coins or DEFAULT_COST[body.level]
    secret = await repo.create(
        session,
        couple_id=couple.id,
        author_id=author.id,
        content=body.content,
        level=body.level,
        cost_coins=cost,
        is_burn_after_read=body.is_burn_after_read,
    )
    await session.commit()
    await session.refresh(secret)
    return secret


async def list_available(
    session: AsyncSession, couple: Couple, user: User
) -> list[SecretListItem]:
    """对方发布的、我还能摘的秘密。

    返回列表项而不是完整对象，确保内容不会随列表泄漏。
    """
    secrets = await repo.list_available(session, couple.id, _partner_id(couple, user.id))
    return [
        SecretListItem(
            id=s.id,
            level=s.level,
            cost_coins=s.cost_coins,
            is_burn_after_read=s.is_burn_after_read,
            status=s.status,
            authored_by_me=False,
            viewed=s.viewed_by is not None,
            created_at=s.created_at,
        )
        for s in secrets
    ]


async def list_mine(
    session: AsyncSession, couple: Couple, user: User
) -> list[SecretListItem]:
    """我发布的全部秘密，包含已燃尽和已销毁的。"""
    secrets = await repo.list_by_author(session, couple.id, user.id)
    return [
        SecretListItem(
            id=s.id,
            level=s.level,
            cost_coins=s.cost_coins,
            is_burn_after_read=s.is_burn_after_read,
            status=s.status,
            authored_by_me=True,
            viewed=s.viewed_by is not None,
            created_at=s.created_at,
        )
        for s in secrets
    ]


async def unlock(
    session: AsyncSession, couple: Couple, viewer: User, secret_id: int
) -> SecretDetail:
    """花金币摘取一条秘密。

    校验顺序（都在行锁内）：
    1. 秘密存在且属于当前关系（防越权）
    2. 不是自己发布的
    3. 状态仍是 active
    4. 没被别人看过（否则不再扣费）

    扣币、标记已读、燃尽、通知在同一个事务里提交。
    """
    secret = await repo.get_for_update(session, secret_id)
    if secret is None or secret.couple_id != couple.id:
        raise AppError("秘密不存在", code=5001, status_code=404)
    if secret.author_id == viewer.id:
        raise AppError("不能摘取自己的秘密", code=5002, status_code=400)
    if secret.status != "active":
        raise AppError("这个秘密已经不可摘取了", code=5003, status_code=409)

    # 非燃尽秘密：看过就不再扣费。
    # 用 commit 而不是 rollback 释放行锁——rollback 会把 ORM 对象置为过期，
    # 之后再读 secret.content 会触发同步 IO。
    if secret.viewed_by is not None:
        await session.commit()
        return _to_detail(secret)

    try:
        # spend_locked 不提交，和下面的状态更新一起 commit
        await coin_service.spend_locked(
            session,
            couple_id=couple.id,
            spender_id=viewer.id,
            amount=secret.cost_coins,
            ref_type="secret",
            ref_id=secret.id,
        )
        secret.viewed_by = viewer.id
        secret.viewed_at = datetime.now(UTC)
        if secret.is_burn_after_read:
            # 只标记状态，内容保留到燃尽期结束
            secret.status = "burned"
        await notification_service.notify(
            session,
            user_id=secret.author_id,
            type="secret.unlocked",
            title="你的秘密被摘取了",
            related_type="secret",
            related_id=secret.id,
        )
        await session.commit()
    except AppError:
        # 金币不足等业务错误：回滚扣币，秘密保持 active
        await session.rollback()
        raise

    await session.refresh(secret)
    return _to_detail(secret)


async def destroy(session: AsyncSession, couple: Couple, user: User, secret_id: int) -> None:
    """销毁自己发布的一条秘密。

    只能销毁自己的：这是信任底线，不能替对方删东西。
    """
    secret = await repo.get_for_update(session, secret_id)
    if secret is None or secret.couple_id != couple.id:
        raise AppError("秘密不存在", code=5001, status_code=404)
    if secret.author_id != user.id:
        raise AppError("只能销毁自己发布的秘密", code=5004, status_code=403)
    await repo.destroy_one(session, secret)
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="secret.destroy",
        target_type="secret",
        target_id=secret.id,
    )
    await session.commit()


async def destroy_all_mine(session: AsyncSession, couple: Couple, user: User) -> int:
    """一键销毁自己发布的全部秘密。

    只影响 author_id = 自己的记录，对方的秘密完全不受影响。
    返回销毁数量。
    """
    count = await repo.destroy_all_of_author(session, couple.id, user.id)
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="secret.destroy_all",
        target_type="secret",
        detail={"count": count},
    )
    await session.commit()
    return count


async def purge_burned(session: AsyncSession) -> int:
    """后台任务：清空燃尽期已过的内容。

    由 worker 每天执行，返回清理条数。
    """
    count = await repo.purge_burned_before(session, datetime.now(UTC) - BURN_GRACE)
    await session.commit()
    return count


def _to_detail(secret: Secret) -> SecretDetail:
    """把 ORM 对象转成接口结构。content 在这里已经是解密后的明文。"""
    return SecretDetail(
        id=secret.id,
        content=secret.content,
        level=secret.level,
        cost_coins=secret.cost_coins,
        is_burn_after_read=secret.is_burn_after_read,
        status=secret.status,
        created_at=secret.created_at,
    )
