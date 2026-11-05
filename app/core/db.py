"""数据库连接与会话。

这里只负责“怎么连”和“怎么给请求分配会话”，
表结构和查询分别在 models.py 与 repository.py。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。

    Alembic 通过 `Base.metadata` 发现全部表；
    因此新增模型后必须在 `app/modules/__init__.py` 里导入一次。
    """


engine = create_async_engine(
    settings.DATABASE_URL,
    # DEBUG=true 时打印 SQL。生产环境务必关闭，否则日志会被 SQL 淹没
    echo=settings.DEBUG,
    # 连接池取连接前先 ping 一次，避免拿到被数据库单方面断开的死连接
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    # 提交后不把对象标记为过期。
    # 否则在异步代码里访问对象属性会触发隐式 IO，直接抛 MissingGreenlet。
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：一个 HTTP 请求一个 session。

    会话在请求结束时自动关闭；如果发生异常则回滚。
    不要在多个并发任务之间共享同一个 session。
    """
    async with SessionLocal() as session:
        yield session
