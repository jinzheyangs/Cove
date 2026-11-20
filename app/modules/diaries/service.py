"""业务层：日记的权限与「各自视角」关联。

权限矩阵：
             读取   修改   删除
personal     双方   作者   作者
shared       双方   双方   双方
"""

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.queue import enqueue_background
from app.core.storage import get_storage
from app.modules.couples.models import Couple
from app.modules.diaries import repository as repo
from app.modules.diaries.models import Diary
from app.modules.diaries.schemas import DiaryCreate, DiaryOut, DiaryUpdate
from app.modules.users.models import User

logger = structlog.get_logger("diaries")


async def _purge_unused_images(
    session: AsyncSession,
    couple_id: int,
    keys: list[str],
    *,
    exclude_diary_id: int | None = None,
) -> None:
    """删掉已经没有任何日记在引用的图片文件。

    图片 key 是 uuid，正常情况下不会共享；但删之前仍查一次引用，
    免得「同一张图被两篇日记引用」时把还在用的图删掉。
    文件删除失败只记日志：业务已经提交，不能因此报错。
    """
    if not keys:
        return

    query = select(Diary.images).where(Diary.couple_id == couple_id)
    if exclude_diary_id is not None:
        query = query.where(Diary.id != exclude_diary_id)
    rows = await session.scalars(query)
    still_used: set[str] = set()
    for images in rows:
        still_used.update(images or [])

    storage = get_storage()
    for key in keys:
        # 历史数据里可能是完整外链，那不是我们存的，跳过
        if not key or key in still_used or key.startswith(("http://", "https://")):
            continue
        try:
            await asyncio.to_thread(storage.delete, key)
        except Exception as exc:  # noqa: BLE001 - 删文件不影响业务结果
            logger.warning("diaries.image_delete_failed", key=key, error=repr(exc))


async def create(
    session: AsyncSession, couple: Couple, author: User, body: DiaryCreate
) -> Diary:
    """新建日记。

    mode 默认 personal：大多数记录是个人视角，
    共同编辑需要双方有意识地选择。
    """
    key = body.idempotency_key
    if key:
        existing = await repo.get_by_idempotency_key(session, couple.id, key)
        if existing is not None:
            return existing

    # 主题也算内容：写一个主题就能存下来，心得和照片可以随后补。
    # 但三者全空是一条既点不开也搜不到的空记录，纯占位，直接拒掉。
    if (
        not (body.title or "").strip()
        and not body.content.strip()
        and not body.images
    ):
        raise AppError(
            "写个主题，或者写点心得、放张照片", code=8004, status_code=400
        )

    try:
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
            idempotency_key=key,
        )
        await session.commit()
    except IntegrityError:
        # 并发提交同一个 key：唯一索引兜底，返回先成功的那条。
        # key 为空时不能去查 NULL，否则可能返回一条无关的旧记录。
        await session.rollback()
        if key:
            existing = await repo.get_by_idempotency_key(session, couple.id, key)
            if existing is not None:
                return existing
        raise

    await session.refresh(diary)
    # 事务提交后再入队，避免索引任务读到未提交的数据
    enqueue_background("index_diary", diary.id)
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
    removed_images: list[str] = []
    if "images" in changes:
        old = set(diary.images or [])
        new = set(changes["images"] or [])
        removed_images = sorted(old - new)
    for field, value in changes.items():
        setattr(diary, field, value)

    # 编辑后也不能变成「主题、正文、图片全空」的空记录
    # （比如清空正文又删掉图片，但主题还在 → 允许，主题本身就算内容）
    new_title = (changes.get("title", diary.title) or "").strip()
    new_content = (changes.get("content", diary.content) or "").strip()
    new_images = changes.get("images", diary.images) or []
    if not new_title and not new_content and not new_images:
        raise AppError(
            "写个主题，或者写点心得、放张照片", code=8004, status_code=400
        )

    await session.commit()
    await session.refresh(diary)
    # 被移除的图片：没有别的日记再用就删掉文件，避免存储里留孤儿
    await _purge_unused_images(
        session, couple.id, removed_images, exclude_diary_id=diary.id
    )
    # 内容变了就重建索引；没变时 index_diary 内部会按 hash 跳过
    enqueue_background("index_diary", diary.id)
    return diary


async def delete(session: AsyncSession, couple: Couple, user: User, diary_id: int) -> None:
    """删除日记。个人视角只有作者能删，共同编辑双方都能删。

    图片会一起清理：先确认没有别的日记还在引用这些 key，再删文件。
    数据库提交在前、删文件在后 —— 文件删失败最多留个孤儿，
    不会出现「日记没了但图片还在被别处引用」。
    """
    diary = await get_one(session, couple, diary_id)
    if diary.mode == "personal" and diary.author_id != user.id:
        raise AppError("只能删除自己的日记", code=8003, status_code=403)
    diary_id = diary.id
    images = list(diary.images or [])
    await repo.delete(session, diary)
    await session.commit()
    await _purge_unused_images(session, couple.id, images)
    # 同步删除向量索引，避免已删内容还能被检索到
    enqueue_background("delete_diary_vectors", diary_id)


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
