"""共同清单表结构。

type 区分共同与单人：
- shared：双方都能看到、都能修改、都能完成
- personal：只有创建者能改，尊重个人空间
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TodoItem(Base):
    """一条清单项。

    category 是自由字符串，前端约定四类：
    想去的地方 / 想一起学的技能 / 想改掉的习惯 / 想实现的约定。
    """

    __tablename__ = "todo_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # shared / personal
    type: Mapped[str] = mapped_column(String(20), default="shared", server_default="shared")
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # pending / completed / cancelled
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    # 个人清单的权限依据
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("type IN ('shared', 'personal')", name="ck_todo_items_type"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')", name="ck_todo_items_status"
        ),
        # 列表按关系 + 类型过滤
        Index("ix_todo_items_couple_type", "couple_id", "type"),
    )
