"""业务层：纪念日与倒计时。

三类条目的来源不同，但对外统一成一种结构：
- 在一起：couples.bind_at，不需要用户录入
- 生日：users.birthday，双方各填自己的
- 自定义：anniversaries 表，双方都能改
"""

import re
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import TZ, today
from app.modules.anniversaries import repository as repo
from app.modules.anniversaries.models import Anniversary
from app.modules.anniversaries.schemas import (
    AnniversaryCreate,
    AnniversaryOut,
    AnniversaryUpdate,
)
from app.modules.couples.models import Couple
from app.modules.users.models import User

# 点节点收藏出来的条目标题：「在一起 · 第 300 天」/「在一起 · 1 周年」
_NODE_DAY = re.compile(r"^(.+?)\s*·\s*第\s*(\d+)\s*天$")
_NODE_YEAR = re.compile(r"^(.+?)\s*·\s*(\d+)\s*周年$")


def _with_year(anchor: date_type, year: int) -> date_type:
    """把日期换到指定年份。

    2 月 29 日在平年落到 2 月 28 日，保证每年都有倒计时。
    """
    try:
        return anchor.replace(year=year)
    except ValueError:
        return date_type(year, 2, 28)


def next_occurrence(
    anchor: date_type, day: date_type, repeat_yearly: bool
) -> date_type:
    """下一次发生的日期。

    - 一次性事件：原日期，不管是否已经过去
    - 每年重复：今年还没过就是今年，已经过了就是明年
    """
    if not repeat_yearly:
        return anchor
    # 第一次发生日在未来：下一次就是它本身，不能倒推到今年
    if anchor > day:
        return anchor

    candidate = _with_year(anchor, day.year)
    if candidate < day:
        candidate = _with_year(anchor, day.year + 1)
    return candidate


def _build_entry(
    *,
    source: str,
    title: str,
    anchor: date_type,
    repeat_yearly: bool,
    day: date_type,
    mode: str = "countdown",
    entry_id: int | None = None,
    owner_id: int | None = None,
    editable: bool = False,
) -> AnniversaryOut:
    next_date = next_occurrence(anchor, day, repeat_yearly)
    days_left = (next_date - day).days
    return AnniversaryOut(
        id=entry_id,
        source=source,
        title=title,
        date=anchor,
        next_date=next_date,
        days_left=days_left,
        years=next_date.year - anchor.year if repeat_yearly else None,
        is_today=days_left == 0,
        passed=days_left < 0,
        repeat_yearly=repeat_yearly,
        mode=mode,
        owner_id=owner_id,
        editable=editable,
    )


def _mode_for(kind: str | None, mode: str | None) -> str:
    """读数方向只看用户选的 mode。

    kind 只是早期的分类残留（custom / wedding），现在页面上只分「目标日 / 起始日」，
    不再让它覆盖用户的选择；存量 wedding 行的 mode 在迁移里已经置成 elapsed。
    """
    return mode or "countdown"


def _guard_elapsed_in_past(mode: str, anchor: date_type, day: date_type) -> None:
    """起始日是「从那天起算」的，起始日不能在未来——否则会显示负数的天数。"""
    if mode == "elapsed" and anchor > day:
        raise AppError(
            "起始日要从已经发生的日子算起，日期不能晚于今天",
            code=18002,
            status_code=422,
        )


def _sort_key(entry: AnniversaryOut) -> tuple[int, int]:
    """未来的按由近到远；已经过去的排在最后，且最近的在前。"""
    if entry.days_left >= 0:
        return (0, entry.days_left)
    return (1, -entry.days_left)


def _node_anchor(title: str | None, rel_title: str, start: date_type) -> date_type | None:
    """「在一起 · 第 N 天 / N 周年」这类条目是从起始日派生出来的。

    用户点节点把它单独收藏成了一条日子，日期当时就落库了；
    起始日一改，库里还是旧日期，首页和页头就会挂着「271 天」这种旧数。
    这里按当前起始日算回正确的日期，读取端一处改、所有页面都对。
    认不出来的标题（自己起的名字）原样返回 None，不动。
    """
    if not title:
        return None
    day_m = _NODE_DAY.match(title)
    if day_m and day_m.group(1).strip() == rel_title:
        return start + timedelta(days=int(day_m.group(2)) - 1)
    year_m = _NODE_YEAR.match(title)
    if year_m and year_m.group(1).strip() == rel_title:
        return _with_year(start, start.year + int(year_m.group(2)))
    return None


async def _bind_day(session: AsyncSession, couple: Couple) -> date_type:
    """关系的起始日期（北京时间）。

    优先用用户填的 start_date；没填时退回绑定那天。
    测试里 couple 可能还没刷新出 server_default，这里补一次。
    """
    if couple.bind_at is None and couple.start_date is None:
        await session.refresh(couple)
    if couple.start_date is not None:
        return couple.start_date
    if couple.bind_at is None:
        return today()
    return couple.bind_at.astimezone(TZ).date()


async def list_entries(
    session: AsyncSession,
    couple: Couple,
    *,
    day: date_type | None = None,
) -> list[AnniversaryOut]:
    """返回全部倒计时条目，按剩余天数排序。"""
    day = day or today()
    entries: list[AnniversaryOut] = []

    # 1. 在一起：直接由绑定时间计算。这是「起点」，主读数看已经多少天
    bind = await _bind_day(session, couple)
    rel_title = "在一起"
    entries.append(
        _build_entry(
            source="relationship",
            title=rel_title,
            anchor=bind,
            repeat_yearly=True,
            day=day,
            mode="elapsed",
        )
    )

    # 2. 双方生日
    users = {
        user.id: user
        for user in await session.scalars(
            select(User).where(User.id.in_([couple.user1_id, couple.user2_id]))
        )
    }
    for user_id in (couple.user1_id, couple.user2_id):
        person = users.get(user_id)
        if person is not None and person.birthday is not None:
            entries.append(
                _build_entry(
                    source="birthday",
                    title=f"{person.nickname}的生日",
                    anchor=person.birthday,
                    repeat_yearly=True,
                    day=day,
                    owner_id=person.id,
                )
            )

    # 3. 自定义纪念日（含结婚纪念日，两者只是 kind 不同）
    for row in await repo.list_by_couple(session, couple.id):
        node = None
        if (row.kind or "custom") == "custom":
            node = _node_anchor(row.title, rel_title, bind)
        entries.append(
            _build_entry(
                source=row.kind or "custom",
                title=row.title,
                anchor=node or row.date,
                repeat_yearly=row.repeat_yearly,
                day=day,
                mode=_mode_for(row.kind, row.mode),
                entry_id=row.id,
                owner_id=row.created_by,
                editable=True,
            )
        )

    entries.sort(key=_sort_key)
    return entries


def to_out(row: Anniversary, *, day: date_type | None = None) -> AnniversaryOut:
    """把自定义纪念日转成统一的倒计时结构。"""
    return _build_entry(
        source=row.kind or "custom",
        title=row.title,
        anchor=row.date,
        repeat_yearly=row.repeat_yearly,
        day=day or today(),
        mode=_mode_for(row.kind, row.mode),
        entry_id=row.id,
        owner_id=row.created_by,
        editable=True,
    )


async def create(
    session: AsyncSession,
    couple: Couple,
    user: User,
    body: AnniversaryCreate,
    *,
    day: date_type | None = None,
) -> AnniversaryOut:
    """新建自定义纪念日。"""
    current = day or today()
    _guard_elapsed_in_past(_mode_for(body.kind, body.mode), body.date, current)

    key = body.idempotency_key
    if key:
        existing = await repo.get_by_idempotency_key(session, couple.id, key)
        if existing is not None:
            return to_out(existing, day=day)

    try:
        row = await repo.create(
            session,
            couple_id=couple.id,
            created_by=user.id,
            title=body.title,
            kind=body.kind,
            mode=_mode_for(body.kind, body.mode),
            date=body.date,
            repeat_yearly=body.repeat_yearly,
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
                return to_out(existing, day=day)
        raise

    await session.refresh(row)
    return to_out(row, day=day)


async def _get_in_couple(
    session: AsyncSession, couple: Couple, anniversary_id: int
) -> Anniversary:
    row = await repo.get(session, anniversary_id)
    if row is None or row.couple_id != couple.id:
        raise AppError("纪念日不存在", code=18001, status_code=404)
    return row


async def update(
    session: AsyncSession,
    couple: Couple,
    anniversary_id: int,
    body: AnniversaryUpdate,
    *,
    day: date_type | None = None,
) -> AnniversaryOut:
    """部分更新。共同纪念日双方都能改。"""
    row = await _get_in_couple(session, couple, anniversary_id)

    if body.title is not None:
        row.title = body.title
    if body.kind is not None:
        row.kind = body.kind
        # 改成结婚纪念日时读数方向跟着变，不留旧的 countdown
        row.mode = _mode_for(body.kind, body.mode)
    elif body.mode is not None:
        row.mode = _mode_for(row.kind, body.mode)
    if body.date is not None:
        row.date = body.date
    if body.repeat_yearly is not None:
        row.repeat_yearly = body.repeat_yearly

    _guard_elapsed_in_past(row.mode, row.date, day or today())

    await session.commit()
    await session.refresh(row)
    return to_out(row, day=day)


async def delete(
    session: AsyncSession, couple: Couple, anniversary_id: int
) -> None:
    row = await _get_in_couple(session, couple, anniversary_id)
    await repo.delete(session, row)
    await session.commit()
