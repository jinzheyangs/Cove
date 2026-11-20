"""情侣关系与邀请码的表结构。

这里的核心约束都在数据库层，而不是只靠代码自觉：
- user1_id < user2_id：同一对关系只有一种存法
- active 状态上的部分唯一索引：一个人同时只能有一段关系
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CoupleInvite(Base):
    """绑定邀请码。

    生命周期：
        active --(被使用)--> used
        active --(过期)----> 逻辑上失效（不主动改状态，靠 expires_at 判断）
    """

    __tablename__ = "couple_invites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 发起绑定的一方
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    # 6 位人类可读码，唯一索引兼作查找索引
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )
    # 24 小时后过期。过期不删记录，方便排查
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Couple(Base):
    """一段情侣关系。

    两个用户 id 始终按大小排序存放（user1_id < user2_id），
    这样 (A,B) 和 (B,A) 不可能同时存在。

    解除绑定只改 status，不删数据：
    双方的日记、秘密、账目仍然保留。
    """

    __tablename__ = "couples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    user2_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # active / unbound
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )
    bind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 「在一起」的起始日，由用户在引导页填写；为空时退回 bind_at 的日期。
    # 绑定动作的时间往往不是真正的相识日，所以单独存一列。
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    # 发起这段关系的人（生成邀请码的人）。
    # 用途：绑定后的「填在一起那天」只该问一次 —— 问发起人，别让被邀请的人
    # 再填一遍同一个日期。老数据为 NULL，前端按原行为处理。
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), default=None
    )
    unbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # user1 永远是小 id，保证 (A,B) 和 (B,A) 不会建成两行
        CheckConstraint("user1_id < user2_id", name="ck_couples_ordered"),
        # 部分唯一索引：只约束 active 的关系。
        # 解除绑定后双方可以各自重新绑定，历史记录不受影响。
        Index(
            "uq_active_couple_u1",
            "user1_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_active_couple_u2",
            "user2_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
