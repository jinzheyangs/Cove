"""业务层：日记的权限与「各自视角」关联。

权限矩阵：
             读取   修改   删除
personal     双方   作者   作者
shared       双方   双方   双方
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.couples.models import Couple
from app.modules.diaries import repository as repo
from app.modules.diaries.models import Diary
from app.modules.diaries.schemas import DiaryCreate, DiaryUpdate
from app.modules.users.models import User


async def create(
    session: AsyncSession, couple: Couple, author: User, body: DiaryCreate
) -> Diary:
    """新建日记。

    mode 默认 personal：大多数记录是个人视角，
    共同编辑需要双方有意识地选择。
    """
    diary = await repo.create(
        session,
        couple_id=couple.id,
        author_id=author.id,
        mode=body.mode,
        title=body.title,
        content=body.content,
        mood_tags=body.mood_tags,
        location=body.location,
        images=body.images,
        event_id=body.event_id,
    )
    await session.commit()
    await session.refresh(diary)
    return diary


async def list_diaries(
    session: AsyncSession,
    couple: Couple,
    *,
    mode: str | None = None,
    event_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Diary]:
    """按关系列出日记。双方看到的是同一份。"""
    return await repo.list_diaries(
        session, couple.id, mode=mode, event_id=event_id, limit=limit, offset=offset
    )


async def get_one(session: AsyncSession, couple: Couple, diary_id: int) -> Diary:
    """读取单篇，并校验它属于当前关系。

    不校验 couple_id 的话，只要猜到 id 就能读到别人的日记。
    """
    diary = await repo.get(session, diary_id)
    if diary is None or diary.couple_id != couple.id:
        raise AppError("日记不存在", code=8001, status_code=404)
    return diary


async def update(
    session: AsyncSession, couple: Couple, user: User, diary_id: int, body: DiaryUpdate
) -> Diary:
    """部分更新。

    先校验越权，再用 exclude_unset 只应用客户端真正传了的字段，
    避免“只改标题”把没传的正文覆盖成 None。
    """
    diary = await get_one(session, couple, diary_id)
    # 个人视角只有作者能改；共同编辑双方都能改
    if diary.mode == "personal" and diary.author_id != user.id:
        raise AppError("只能修改自己的日记", code=8002, status_code=403)

    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(diary, field, value)

    await session.commit()
    await session.refresh(diary)
    return diary


async def delete(session: AsyncSession, couple: Couple, user: User, diary_id: int) -> None:
    """删除日记。个人视角只有作者能删，共同编辑双方都能删。"""
    diary = await get_one(session, couple, diary_id)
    if diary.mode == "personal" and diary.author_id != user.id:
        raise AppError("只能删除自己的日记", code=8003, status_code=403)
    await repo.delete(session, diary)
    await session.commit()
