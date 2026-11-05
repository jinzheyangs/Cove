"""数据访问层：账号删除与数据导出。

这是横跨多个模块的隐私操作，单独放在 privacy 下，
避免 users 模块反过来依赖所有业务模块。
"""

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.bills.models import Bill
from app.modules.coin_applies.models import CoinApply
from app.modules.coins.models import CoinTransaction
from app.modules.conflicts.models import ConflictMessage, ConflictReview
from app.modules.daily.models import DailyAnswer
from app.modules.diaries.models import Diary
from app.modules.inquiries.models import InquiryInput, InquirySupplement
from app.modules.secrets.models import Secret
from app.modules.simta.models import PersonaConsent, PersonaSettings
from app.modules.todos.models import TodoItem


async def purge_personal_content(session: AsyncSession, user_id: int) -> None:
    """删除用户自己产生的内容。

    保留金币流水和商城记录：它们是双方共用的账目，
    删除会让对方的余额和订单对不上。用户行会被匿名化。
    """
    targets = (
        (Secret, Secret.author_id),
        (Diary, Diary.author_id),
        (Bill, Bill.payer_id),
        (TodoItem, TodoItem.creator_id),
        (DailyAnswer, DailyAnswer.user_id),
        (InquiryInput, InquiryInput.user_id),
        (InquirySupplement, InquirySupplement.user_id),
        (ConflictReview, ConflictReview.user_id),
        (ConflictMessage, ConflictMessage.user_id),
        (PersonaConsent, PersonaConsent.user_id),
        (PersonaSettings, PersonaSettings.owner_id),
        (CoinApply, CoinApply.applicant_id),
        (AuditLog, AuditLog.user_id),
    )
    for model, column in targets:
        await session.execute(delete(model).where(column == user_id))
    await session.flush()


async def collect_export(session: AsyncSession, user_id: int) -> dict[str, list]:
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
    reviews = list(
        await session.scalars(
            select(ConflictReview)
            .where(ConflictReview.user_id == user_id)
            .order_by(ConflictReview.id)
        )
    )
    inputs = list(
        await session.scalars(
            select(InquiryInput)
            .where(InquiryInput.user_id == user_id)
            .order_by(InquiryInput.id)
        )
    )
    supplements = list(
        await session.scalars(
            select(InquirySupplement)
            .where(InquirySupplement.user_id == user_id)
            .order_by(InquirySupplement.id)
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
        "reviews": reviews,
        "inputs": inputs,
        "supplements": supplements,
        "transactions": transactions,
    }
