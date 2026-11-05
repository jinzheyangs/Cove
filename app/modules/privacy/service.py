"""业务层：注销账号与导出个人数据。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
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

    # 1. 解除当前关系，但保留历史记录供对方导出
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


# 导出时每类数据保留的字段。显式列出来，避免把内部字段（如 user_id）带出去
_DIARY_FIELDS = (
    "id",
    "mode",
    "event_id",
    "title",
    "content",
    "mood_tags",
    "location",
    "images",
    "created_at",
)
_SECRET_FIELDS = ("id", "level", "cost_coins", "status", "content", "created_at")
_BILL_FIELDS = (
    "id",
    "amount",
    "category",
    "type",
    "scope",
    "is_private",
    "remark",
    "created_at",
)
_TODO_FIELDS = (
    "id",
    "type",
    "category",
    "title",
    "description",
    "status",
    "completed_at",
    "created_at",
)
_DAILY_FIELDS = ("day", "question", "answer", "created_at")
_REVIEW_FIELDS = (
    "session_id",
    "want_to_be_understood",
    "heard_partner_need",
    "created_at",
)
_INPUT_FIELDS = ("session_id", "content", "created_at")
_TX_FIELDS = ("id", "type", "amount", "ref_type", "ref_id", "remark", "created_at")


def _pick(obj: object, fields: tuple[str, ...]) -> dict:
    """从 ORM 对象里挑出指定字段，转成可 JSON 序列化的 dict。

    加密字段读出来时已经由 ORM 自动解密。
    """
    return {field: getattr(obj, field) for field in fields}


async def export_data(session: AsyncSession, user: User) -> dict:
    """导出个人数据。

    返回一个可直接 JSON 序列化的字典：
    资料、关系、日记、秘密、账本、清单、每日一问、复盘、询问、金币流水。
    """
    couple = await couple_repo.get_active_by_user(session, user.id)
    raw = await repo.collect_export(session, user.id)

    return {
        "profile": {
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "created_at": user.created_at,
        },
        "couple": (
            {
                "id": couple.id,
                "bind_at": couple.bind_at,
                "status": couple.status,
            }
            if couple
            else None
        ),
        "diaries": [_pick(d, _DIARY_FIELDS) for d in raw["diaries"]],
        "secrets": [_pick(s, _SECRET_FIELDS) for s in raw["secrets"]],
        "bills": [_pick(b, _BILL_FIELDS) for b in raw["bills"]],
        "todos": [_pick(t, _TODO_FIELDS) for t in raw["todos"]],
        "daily": [_pick(d, _DAILY_FIELDS) for d in raw["daily"]],
        "conflict_reviews": [_pick(r, _REVIEW_FIELDS) for r in raw["reviews"]],
        "inquiry_inputs": [_pick(i, _INPUT_FIELDS) for i in raw["inputs"]],
        "inquiry_supplements": [_pick(s, _INPUT_FIELDS) for s in raw["supplements"]],
        "coin_transactions": [_pick(t, _TX_FIELDS) for t in raw["transactions"]],
    }
