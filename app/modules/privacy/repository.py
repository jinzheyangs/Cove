"""数据访问层：账号删除与数据导出。

这是横跨多个模块的隐私操作，单独放在 privacy 下，
避免 users 模块反过来依赖所有业务模块。
"""

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.models import (
    AgentConversation,
    ChatImport,
    ChatMessage,
    PersonaProfile,
)
from app.modules.ai.models import ChunkIndex
from app.modules.audit.models import AuditLog
from app.modules.bills.models import Bill
from app.modules.coin_applies.models import CoinApply
from app.modules.coins.models import CoinTransaction
from app.modules.daily.models import DailyAnswer
from app.modules.diaries.models import Diary
from app.modules.notifications.models import Notification
from app.modules.secrets.models import Secret
from app.modules.simta.models import PersonaConsent, PersonaSettings
from app.modules.todos.models import TodoItem
from app.modules.users.models import RefreshToken


async def collect_chat_imports(
    session: AsyncSession, couple_id: int | None, user_id: int
) -> tuple[list[int], list[int]]:
    """注销前记录需要处理的聊天导入。

    Returns:
        (uploaded, affected)
        - uploaded：本人上传的导入，整条删除
        - affected：对方上传、但包含本人发言的导入，删掉本人发言后需要重建索引
    """
    if couple_id is None:
        return [], []

    uploaded = list(
        await session.scalars(
            select(ChatImport.id).where(
                ChatImport.couple_id == couple_id,
                ChatImport.uploaded_by == user_id,
            )
        )
    )
    affected = list(
        await session.scalars(
            select(ChatMessage.import_id)
            .where(
                ChatMessage.couple_id == couple_id,
                ChatMessage.sender_id == user_id,
            )
            .distinct()
        )
    )
    uploaded_set = set(uploaded)
    return uploaded, [import_id for import_id in affected if import_id not in uploaded_set]


async def purge_personal_content(session: AsyncSession, user_id: int) -> None:
    """删除用户自己产生的内容。

    删除范围：秘密、日记、账本、清单、每日一问、模拟TA 授权、通知、审计，
    以及 Agent 会话、聊天导入、画像和刷新令牌。

    **保留**金币流水和商城记录：
    它们是双方共用的账目，删除会让对方的余额和订单对不上。
    用户行会被匿名化，外键仍然有效。

    注意：这里用批量 DELETE，不经过 ORM，
    所以加密字段不需要解密，性能也更好。
    """
    targets = (
        (Secret, Secret.author_id),
        (Diary, Diary.author_id),
        (Bill, Bill.payer_id),
        (TodoItem, TodoItem.creator_id),
        (DailyAnswer, DailyAnswer.user_id),
        (PersonaConsent, PersonaConsent.user_id),
        (PersonaSettings, PersonaSettings.owner_id),
        (CoinApply, CoinApply.applicant_id),
        (Notification, Notification.user_id),
        (AuditLog, AuditLog.user_id),
    )
    for model, column in targets:
        await session.execute(delete(model).where(column == user_id))

    # 本人上传的聊天记录：连同对方在这个文件里的发言一起删掉。
    # 先用子查询取出 id，再按顺序删除，避免外键悬挂。
    uploaded_imports = select(ChatImport.id).where(ChatImport.uploaded_by == user_id)
    await session.execute(
        delete(ChatMessage).where(ChatMessage.import_id.in_(uploaded_imports))
    )
    await session.execute(
        delete(ChunkIndex).where(
            ChunkIndex.source_type == "chat",
            ChunkIndex.source_id.in_(uploaded_imports),
        )
    )
    await session.execute(delete(ChatImport).where(ChatImport.uploaded_by == user_id))

    # 对方上传的记录里，本人说过的话也要删掉；对方的发言保留。
    await session.execute(delete(ChatMessage).where(ChatMessage.sender_id == user_id))

    # 会话消息和待确认动作由外键 ON DELETE CASCADE 一起删除。
    await session.execute(
        delete(AgentConversation).where(AgentConversation.owner_id == user_id)
    )
    await session.execute(
        delete(PersonaProfile).where(PersonaProfile.user_id == user_id)
    )
    # 刷新令牌一并清理，避免已注销账号的令牌行长期残留。
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.flush()


async def collect_export(session: AsyncSession, user_id: int) -> dict[str, list]:
    """收集该用户产生的内容，供导出接口组装。

    只导出本人写的内容，不导出对方的。
    金币流水三个字段都查：收到的、花掉的、发起赠与的。
    """
    diaries = list(
        await session.scalars(
            select(Diary).where(Diary.author_id == user_id).order_by(Diary.id)
        )
    )
    secrets = list(
        await session.scalars(
            select(Secret).where(Secret.author_id == user_id).order_by(Secret.id)
        )
    )
    bills = list(
        await session.scalars(
            select(Bill).where(Bill.payer_id == user_id).order_by(Bill.id)
        )
    )
    todos = list(
        await session.scalars(
            select(TodoItem).where(TodoItem.creator_id == user_id).order_by(TodoItem.id)
        )
    )
    daily = list(
        await session.scalars(
            select(DailyAnswer).where(DailyAnswer.user_id == user_id).order_by(DailyAnswer.id)
        )
    )
    transactions = list(
        await session.scalars(
            select(CoinTransaction)
            .where(
                or_(
                    CoinTransaction.from_user_id == user_id,
                    CoinTransaction.to_user_id == user_id,
                    CoinTransaction.actor_id == user_id,
                )
            )
            .order_by(CoinTransaction.id)
        )
    )

    return {
        "diaries": diaries,
        "secrets": secrets,
        "bills": bills,
        "todos": todos,
        "daily": daily,
        "transactions": transactions,
    }
