"""业务层：注销账号。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.queue import enqueue
from app.core.security import hash_password, verify_password
from app.modules.audit import service as audit_service
from app.modules.couples import repository as couple_repo
from app.modules.privacy import repository as repo
from app.modules.users.models import User


async def delete_account(session: AsyncSession, user: User, password: str) -> None:
    """注销账号。

    为什么是匿名化而不是物理删除：
    couples / coin_transactions / mall_orders 都还引用这个 user_id，
    硬删会破坏外键，也会让对方的余额和订单对不上。

    流程：
    1. 校验密码（防 token 被盗后恶意注销）
    2. 解除当前关系（历史数据保留）
    3. 删除个人内容
    4. 匿名化用户行：手机号脱敏、密码随机化、标记 deleted_at
    5. 写审计日志并提交
    """
    if not verify_password(password, user.password_hash):
        raise AppError("密码错误", code=15001, status_code=403)

    # 1. 解除当前关系，但保留历史记录供对方查看
    couple = await couple_repo.get_active_by_user(session, user.id)
    if couple is not None:
        couple.status = "unbound"
        couple.unbound_at = datetime.now(UTC)

    # 2. 删除个人内容（金币流水和商城记录保留，否则对方账目会对不上）
    await repo.purge_personal_content(session, user.id)

    # 3. 匿名化用户行，保留外键完整性。
    #    手机号改成 deleted-{id}，把原手机号释放出来，用户可以重新注册
    user.phone = f"deleted-{user.id}"
    user.password_hash = hash_password(uuid4().hex)
    user.nickname = "已注销"
    user.avatar = None
    user.birthday = None
    user.deleted_at = datetime.now(UTC)

    # 审计记录在清理之后写，保证它不会被 purge 掉
    await audit_service.record(
        session,
        user_id=user.id,
        action="user.delete",
        target_type="user",
        target_id=user.id,
    )
    await session.commit()

    # 删除该用户在向量库里的全部索引。
    # 注销是彻底离开，按 user_id 全局删（couple_id 传 None）：
    # 只删「当前这段关系」的话，以前解除过的关系留下的向量会躺在库里没人管。
    await enqueue("delete_user_vectors", None, user.id)
