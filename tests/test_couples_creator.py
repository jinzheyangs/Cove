"""关系创建时记下「谁发起的」。

约定的产品规则：绑定后的「在一起那天」只问一次 —— 问发起人（生成邀请码的人），
拿码绑进来的那一方不再被引导重复填同一个日期。前端就是靠 created_by 判断
谁是发起人的，所以这一列必须真的写入。
"""

from datetime import date

from app.modules.couples import service as couple_service
from app.modules.users.models import User
from tests.helpers import _PASSWORD_HASH


async def _two_new_users(session):
    a = User(phone="13900000011", password_hash=_PASSWORD_HASH, nickname="A")
    b = User(phone="13900000012", password_hash=_PASSWORD_HASH, nickname="B")
    session.add_all([a, b])
    await session.flush()
    return a, b


async def test_bind_records_inviter_as_creator(session):
    a, b = await _two_new_users(session)
    invite = await couple_service.create_invite(session, a)

    couple = await couple_service.bind(session, b, invite.code)

    # 发起邀请的人是 a，拿码绑进来的是 b
    assert couple.created_by == a.id
    assert couple.created_by != b.id


async def test_creator_survives_ordering_of_user_ids(session):
    """bind 会把两个人的 id 排序后写进 user1/user2，created_by 不能被一起排序掉。"""
    a, b = await _two_new_users(session)
    invite = await couple_service.create_invite(session, b)   # 大 id 发起

    couple = await couple_service.bind(session, a, invite.code)  # 小 id 拿码加入

    assert couple.user1_id == a.id and couple.user2_id == b.id
    assert couple.created_by == b.id


async def test_start_date_writable_by_both(session):
    """引导上只问发起人；但填完之后两个人谁都能改，不被身份锁住。"""
    a, b = await _two_new_users(session)
    invite = await couple_service.create_invite(session, a)
    couple = await couple_service.bind(session, b, invite.code)

    await couple_service.update_start_date(session, couple, date(2024, 6, 1))
    assert couple.start_date == date(2024, 6, 1)

    # 被邀请的一方也能改
    await couple_service.update_start_date(session, couple, date(2024, 7, 1))
    assert couple.start_date == date(2024, 7, 1)
