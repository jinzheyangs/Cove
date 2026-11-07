"""用户与刷新令牌的表结构。"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """账号。

    注销采用「匿名化」而不是物理删除：
    couples / coin_transactions 等表还引用这个 id，
    硬删会破坏外键和对方的账目。deleted_at 非空即视为已注销，
    登录和刷新令牌都会拒绝已注销账号。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 手机号同时作为登录名。没有做短信验证，因此它本质上是用户名
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    # argon2 哈希，长度足够放下算法参数
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50))
    avatar: Mapped[str | None] = mapped_column(String(255), default=None)
    # 生日。只用于纪念日倒计时，不作为身份核验信息
    birthday: Mapped[date | None] = mapped_column(Date, default=None)
    # 非空表示账号已注销（数据已清理、手机号已脱敏）
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 数据库侧生成时间，避免应用服务器时钟不一致
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RefreshToken(Base):
    """刷新令牌。

    只存 SHA-256 哈希，不存原文：
    数据库泄露时攻击者也无法直接拿去换 access token。

    轮换策略：每次刷新都把旧记录标记 revoked_at，再插入一条新的。
    如果旧 token 被再次使用，会被判为已吊销并拒绝。
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 64 位十六进制，正好是 sha256 的长度；唯一索引兼作查找索引
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 非空表示已吊销（主动登出、轮换或全量登出）
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # 按用户批量吊销时走这个索引
        Index("ix_refresh_tokens_user", "user_id"),
    )
