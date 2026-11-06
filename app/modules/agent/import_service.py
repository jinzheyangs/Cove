"""聊天记录导入。

职责：
- 校验双方授权
- 解析文件、映射发送人、去重、入库
- 入队做画像和向量索引

原始文件只在内存里处理，不落盘。
"""

import hashlib
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.queue import enqueue
from app.modules.agent import importers, persona
from app.modules.agent.models import ChatImport, ChatMessage, PersonaProfile
from app.modules.ai import indexing
from app.modules.couples.models import Couple
from app.modules.simta import repository as persona_repo
from app.modules.users.models import User

logger = structlog.get_logger("chat_import")

_BATCH_SIZE = 1000


def _partner_id(couple: Couple, user_id: int) -> int:
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def _require_mutual_consent(session: AsyncSession, couple: Couple) -> None:
    """导入会同时使用两个人的数据，必须双方都授权。"""
    for user_id in (couple.user1_id, couple.user2_id):
        consent = await persona_repo.get_consent(session, couple.id, user_id)
        if consent is None or not consent.authorized:
            raise AppError(
                "双方都授权后才能导入聊天记录", code=17002, status_code=403
            )


async def import_chat_log(
    session: AsyncSession,
    couple: Couple,
    uploader: User,
    *,
    filename: str,
    fmt: str,
    raw: bytes,
    owner_name: str | None = None,
    partner_name: str | None = None,
) -> ChatImport:
    """解析并入库。

    同一份文件重复导入不会产生重复消息：
    靠 (couple_id, source_hash) 唯一索引去重。
    """
    await _require_mutual_consent(session, couple)      #授权判断

    # 拉取对方信息，同时验证关系
    partner = await session.get(User, _partner_id(couple, uploader.id))
    if partner is None:
        raise AppError("伴侣不存在", code=17006, status_code=404)

    text = raw.decode("utf-8-sig", errors="replace")    #二进制转文本
    parsed = importers.parse_messages(text, fmt)        #拆聊天记录，传回结构化列表

    if len(parsed.messages) > settings.CHAT_IMPORT_MAX_MESSAGES:
        raise AppError(
            "单次导入的消息太多了，请拆分文件", code=17003, status_code=413
        )

    owner_names = {owner_name.strip()} if owner_name else set()
    owner_names.add(uploader.nickname)
    partner_names = {partner_name.strip()} if partner_name else set()
    partner_names.add(partner.nickname)

    import_row = ChatImport(
        couple_id=couple.id,
        uploaded_by=uploader.id,
        filename=filename,
        format=fmt,
        status="processing",
        total_messages=len(parsed.messages),
        skipped_messages=parsed.skipped,
    )
    session.add(import_row)
    await session.flush()

    values: list[dict] = []     #有效消息
    seen: set[str] = set()      #去重的临时集合
    skipped = parsed.skipped    #计数器（错误）

    for message in parsed.messages:
        sender_name = message.sender.strip()        #发件人昵称
        if sender_name in owner_names:
            sender_id = uploader.id
        elif sender_name in partner_names:
            sender_id = partner.id
        else:
            # 群聊里的第三方、或者导出工具带的系统消息
            skipped += 1
            continue

        digest = hashlib.sha256(
            f"{couple.id}|{sender_id}|{message.sent_at.isoformat()}|{message.content}".encode()
        ).hexdigest()
        if digest in seen:
            skipped += 1
            continue
        seen.add(digest)

        values.append(
            {
                "couple_id": couple.id,
                "import_id": import_row.id,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sent_at": message.sent_at,
                "content": message.content,
                "msg_type": message.msg_type,
                "source_hash": digest,
            }
        )

    # 防止名字映射错误导致所有人的消息都被算到同一个人头上。
    # 双方都该有消息；只有一方说明 owner_name / partner_name 填错了。
    if not values:
        raise AppError("没有可导入的消息", code=17009, status_code=400)

    # 统计我自己的消息条数
    owner_count = sum(
        1 for value in values if value["sender_id"] == uploader.id
    )
    if owner_count == 0 or owner_count == len(values):
        raise AppError(
            "只识别到一方的消息，请检查 owner_name / partner_name 是否和文件里的名字一致",
            code=17008,
            status_code=400,
        )

    imported = 0
    for start in range(0, len(values), _BATCH_SIZE):
        batch = values[start : start + _BATCH_SIZE]
        result = await session.execute(
            pg_insert(ChatMessage)
            .values(batch)
            .on_conflict_do_nothing(index_elements=["couple_id", "source_hash"])
        )
        imported += result.rowcount or 0

    import_row.imported_messages = imported
    import_row.skipped_messages = skipped
    await session.commit()
    await session.refresh(import_row)

    # 画像和向量索引都比较慢，交给 worker
    await enqueue("process_chat_import", import_row.id)
    logger.info(
        "chat_import.stored",
        import_id=import_row.id,
        imported=imported,
        skipped=skipped,
    )
    return import_row


async def process_chat_import(session: AsyncSession, import_id: int) -> None:
    """worker 任务：生成画像 + 建向量索引。"""
    import_row = await session.get(ChatImport, import_id)
    if import_row is None:
        return

    try:
        couple = await session.get(Couple, import_row.couple_id)
        if couple is not None:
            await persona.build_profile(session, couple.id, couple.user1_id)
            await persona.build_profile(session, couple.id, couple.user2_id)

        windows = await indexing.index_chat_import(session, import_id)

        import_row.status = "done"
        import_row.indexed_windows = windows
        import_row.finished_at = datetime.now(UTC)
        await session.commit()
        logger.info("chat_import.done", import_id=import_id, windows=windows)

    except Exception as exc:  # noqa: BLE001 - 失败要记录下来，方便重试
        await session.rollback()
        row = await session.get(ChatImport, import_id)
        if row is not None:
            row.status = "failed"
            row.error = str(exc)[:500]
            row.finished_at = datetime.now(UTC)
            await session.commit()
        logger.warning("chat_import.failed", import_id=import_id, error=repr(exc))


async def list_imports(
    session: AsyncSession, couple: Couple
) -> list[ChatImport]:
    stmt = (
        select(ChatImport)
        .where(ChatImport.couple_id == couple.id)
        .order_by(ChatImport.id.desc())
    )
    return list(await session.scalars(stmt))


async def get_import(
    session: AsyncSession, couple: Couple, import_id: int
) -> ChatImport:
    row = await session.get(ChatImport, import_id)
    if row is None or row.couple_id != couple.id:
        raise AppError("导入记录不存在", code=17007, status_code=404)
    return row


async def delete_import(
    session: AsyncSession, couple: Couple, import_id: int
) -> None:
    """删除一次导入：消息、向量、画像一起清掉。

    画像依赖全部消息，删完会从剩余消息重建。
    """
    row = await get_import(session, couple, import_id)

    await indexing.delete_chat_import(session, import_id)
    await session.execute(
        delete(ChatMessage).where(ChatMessage.import_id == import_id)
    )
    await session.execute(
        delete(PersonaProfile).where(PersonaProfile.couple_id == couple.id)
    )
    await session.delete(row)
    await session.commit()

    # 从剩余聊天记录重新生成画像；没有剩余则保持为空
    for user_id in (couple.user1_id, couple.user2_id):
        await persona.build_profile(session, couple.id, user_id)
