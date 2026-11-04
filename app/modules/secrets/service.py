"""业务层：秘密的发布、摘取、燃尽与销毁。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.secrets import repository as repo
from app.modules.secrets.models import Secret
from app.modules.secrets.schemas import DEFAULT_COST, SecretCreate, SecretDetail, SecretListItem
from app.modules.users.models import User

# 阅后即焚的燃尽期：内容先保留这么久，之后由后台任务清空
BURN_GRACE = timedelta(hours=24)


def _partner_id(couple: Couple, user_id: int) -> int:
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def publish(
    session: AsyncSession, couple: Couple, author: User, body: SecretCreate
) -> Secret:
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
            secret.status = "burned"
        await session.commit()
    except AppError:
        await session.rollback()
        raise

    await session.refresh(secret)
    return _to_detail(secret)


async def destroy(session: AsyncSession, couple: Couple, user: User, secret_id: int) -> None:
    secret = await repo.get_for_update(session, secret_id)
    if secret is None or secret.couple_id != couple.id:
        raise AppError("秘密不存在", code=5001, status_code=404)
    if secret.author_id != user.id:
        raise AppError("只能销毁自己发布的秘密", code=5004, status_code=403)
    await repo.destroy_one(session, secret)
    await session.commit()


async def destroy_all_mine(session: AsyncSession, couple: Couple, user: User) -> int:
    """只销毁自己发布的，不触碰对方的秘密。"""
    count = await repo.destroy_all_of_author(session, couple.id, user.id)
    await session.commit()
    return count


async def purge_burned(session: AsyncSession) -> int:
    count = await repo.purge_burned_before(session, datetime.now(UTC) - BURN_GRACE)
    await session.commit()
    return count


def _to_detail(secret: Secret) -> SecretDetail:
    return SecretDetail(
        id=secret.id,
        content=secret.content,
        level=secret.level,
        cost_coins=secret.cost_coins,
        is_burn_after_read=secret.is_burn_after_read,
        status=secret.status,
        created_at=secret.created_at,
    )
