"""业务层：秘密的发布、摘取与销毁。

摘取是这里最关键的操作：
「扣金币」和「看完即销毁」必须在同一个事务里，
否则会出现扣了钱但秘密还在、或者秘密没了但没扣钱。

规则只有一条：一片叶子只能被读一次，读完就没了。
"""

from datetime import UTC, datetime

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
    """我发布的全部秘密，包含被摘走和已销毁的。"""
    secrets = await repo.list_by_author(session, couple.id, user.id)
    return [
        SecretListItem(
            id=s.id,
            level=s.level,
            cost_coins=s.cost_coins,
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
    """花金币摘取一条秘密，读完立刻销毁。

    校验顺序（都在行锁内）：
    1. 秘密存在且属于当前关系（防越权）
    2. 不是自己发布的
    3. 状态仍是 active（读过一次就已经销毁了，不存在「再读一次免费」）

    扣币、标记已读、通知、销毁在同一个事务里提交。
    内容只在这一个响应里给出：先取出正文构造响应，再清空并置为 destroyed，
    所以同一片叶子不可能被读第二次。
    """
    secret = await repo.get_for_update(session, secret_id)
    if secret is None or secret.couple_id != couple.id:
        raise AppError("秘密不存在", code=5001, status_code=404)
    if secret.author_id == viewer.id:
        raise AppError("不能摘取自己的秘密", code=5002, status_code=400)
    if secret.status != "active":
        raise AppError("这个秘密已经不可摘取了", code=5003, status_code=409)

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
        await notification_service.notify(
            session,
            user_id=secret.author_id,
            type="secret.unlocked",
            title="你的秘密被摘走了",
            related_type="secret",
            related_id=secret.id,
        )
        # 先把这条响应要的内容抓在手里，再落销毁，最后一起提交
        detail = _to_detail(secret)
        await repo.destroy_one(session, secret)
        detail.status = "destroyed"
        await session.commit()
    except AppError:
        # 金币不足等业务错误：回滚扣币，秘密保持 active
        await session.rollback()
        raise

    return detail


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


def _to_detail(secret: Secret) -> SecretDetail:
    """把 ORM 对象转成接口结构。content 在这里已经是解密后的明文。"""
    return SecretDetail(
        id=secret.id,
        content=secret.content,
        level=secret.level,
        cost_coins=secret.cost_coins,
        status=secret.status,
        created_at=secret.created_at,
    )
