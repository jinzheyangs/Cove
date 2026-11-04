"""业务层：询问中心。

流程：双方各自匿名写 → 都提交后由 AI 汇总 → 补充意见 → 关闭。
AI 只做一次固定调用，不走 agent。
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.ai import client as ai_client
from app.modules.couples.models import Couple
from app.modules.inquiries import repository as repo
from app.modules.inquiries.models import InquirySession
from app.modules.inquiries.schemas import InquiryOut
from app.modules.users.models import User

SYSTEM_PROMPT = (
    "你是一个中立的关系顾问。用户提供了两个人分别匿名写下的真实想法。"
    "请按以下结构回答：\n"
    "1. 分别概括双方真正在意的是什么（不要评判谁对谁错）\n"
    "2. 指出你们其实一致的共同点\n"
    "3. 给出 2-3 个双方都能接受的、可执行的方案\n"
    "语气温和、具体，不要说教，不要站队。"
)


async def create(session: AsyncSession, couple: Couple, question: str) -> InquirySession:
    item = await repo.create_session(session, couple.id, question)
    await session.commit()
    await session.refresh(item)
    return item


async def submit_input(
    session: AsyncSession, couple: Couple, user: User, session_id: int, content: str
) -> InquirySession:
    item = await _get(session, couple, session_id)
    if item.status != "collecting":
        raise AppError("已经进入下一阶段，不能修改了", code=13001, status_code=409)

    await repo.upsert_input(session, item.id, user.id, content)
    await session.commit()
    await session.refresh(item)
    return item


async def generate(session: AsyncSession, couple: Couple, session_id: int) -> InquirySession:
    item = await _get(session, couple, session_id)
    if item.status != "collecting":
        raise AppError("这个询问已经生成过了", code=13002, status_code=409)

    inputs = await repo.list_inputs(session, item.id)
    if len(inputs) < 2:
        raise AppError("双方都写完之后才能生成", code=13003, status_code=409)

    item.status = "ai_processing"
    await session.flush()

    prompt = (
        f"问题：{item.question}\n\n"
        + "\n\n".join(f"想法 {i + 1}：{x.content}" for i, x in enumerate(inputs))
    )
    response = await ai_client.complete(system=SYSTEM_PROMPT, user=prompt)

    item.ai_response = response
    item.status = "reviewing"
    await session.commit()
    await session.refresh(item)
    return item


async def supplement(
    session: AsyncSession, couple: Couple, user: User, session_id: int, content: str
) -> InquirySession:
    item = await _get(session, couple, session_id)
    if item.status != "reviewing":
        raise AppError("现在还不能补充意见", code=13004, status_code=409)

    await repo.add_supplement(session, item.id, user.id, content)
    await session.commit()
    await session.refresh(item)
    return item


async def close(session: AsyncSession, couple: Couple, session_id: int) -> InquirySession:
    item = await _get(session, couple, session_id)
    if item.status != "reviewing":
        raise AppError("当前状态不能关闭", code=13005, status_code=409)

    item.status = "closed"
    item.closed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(item)
    return item


async def get_detail(
    session: AsyncSession, couple: Couple, user: User, session_id: int
) -> InquiryOut:
    item = await _get(session, couple, session_id)
    inputs = await repo.list_inputs(session, item.id)
    supplements = await repo.list_supplements(session, item.id)

    both_submitted = len(inputs) >= 2
    my_input = next((x for x in inputs if x.user_id == user.id), None)

    return InquiryOut(
        id=item.id,
        question=item.question,
        status=item.status,
        ai_response=item.ai_response,
        submitted_count=len(inputs),
        my_input_submitted=my_input is not None,
        inputs=[x.content for x in inputs] if both_submitted else [],
        supplements=[s.content for s in supplements],
        created_at=item.created_at,
        closed_at=item.closed_at,
    )


async def _get(session: AsyncSession, couple: Couple, session_id: int) -> InquirySession:
    item = await repo.get_session(session, session_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("询问不存在", code=13006, status_code=404)
    return item
