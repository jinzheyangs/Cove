"""业务层：日记的权限与「各自视角」关联。

权限矩阵：
             读取   修改   删除
personal     双方   作者   作者
shared       双方   双方   双方
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.queue import enqueue
from app.core.storage import get_storage
from app.modules.couples.models import Couple
from app.modules.diaries import repository as repo
from app.modules.diaries.models import Diary
from app.modules.diaries.schemas import DiaryCreate, DiaryOut, DiaryUpdate
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
    # 事务提交后再入队，避免索引任务读到未提交的数据
    await enqueue("index_diary", diary.id)
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
    # 内容变了就重建索引；没变时 index_diary 内部会按 hash 跳过
    await enqueue("index_diary", diary.id)
    return diary


async def delete(session: AsyncSession, couple: Couple, user: User, diary_id: int) -> None:
    """删除日记。个人视角只有作者能删，共同编辑双方都能删。

    注意：这里不级联删除图片。图片可能被多篇日记引用，
    而且删除是不可逆操作，交给前端显式调用 DELETE /uploads/{key} 更安全。
    """
    diary = await get_one(session, couple, diary_id)
    if diary.mode == "personal" and diary.author_id != user.id:
        raise AppError("只能删除自己的日记", code=8003, status_code=403)
    diary_id = diary.id
    await repo.delete(session, diary)
    await session.commit()
    # 同步删除向量索引，避免已删内容还能被检索到
    await enqueue("delete_diary_vectors", diary_id)


def to_out(diary: Diary) -> DiaryOut:
    """把 ORM 对象转成接口结构。

    数据库里存的是 object key，这里按当前存储配置生成可访问 URL。
    私有 OSS 桶生成的是有有效期的签名 URL，所以不要把 image_urls 入库。
    """
    storage = get_storage()
    return DiaryOut(
        id=diary.id,
        event_id=diary.event_id,
        mode=diary.mode,
        title=diary.title,
        content=diary.content,
        mood_tags=diary.mood_tags,
        location=diary.location,
        images=diary.images,
        image_urls=[storage.build_url(key) for key in diary.images],
        author_id=diary.author_id,
        created_at=diary.created_at,
        updated_at=diary.updated_at,
    )
