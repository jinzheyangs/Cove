"""业务层：询问中心。

流程：双方各自匿名写 → 都提交后由 AI 汇总 → 补充意见 → 关闭。
AI 只做一次固定调用，不走 agent——流程是确定的，不需要模型自己决定下一步。
"""

from datetime import UTC, datetime

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

# AI 不可用时的错误码：未配置 / 熔断或调用失败
_AI_UNAVAILABLE = (11001, 11003)


async def create(session: AsyncSession, couple: Couple, question: str) -> InquirySession:
    """发起一次询问，进入 collecting 阶段。"""
    item = await repo.create_session(session, couple.id, question)
    await session.commit()
    await session.refresh(item)
    return item


async def submit_input(
    session: AsyncSession, couple: Couple, user: User, session_id: int, content: str
) -> InquirySession:
    """提交/修改自己的真实想法。

    只在 collecting 阶段允许：
    一旦生成 AI 回复，输入就冻结，避免事后篡改。
    """
    item = await _get(session, couple, session_id)
    if item.status != "collecting":
        raise AppError("已经进入下一阶段，不能修改了", code=13001, status_code=409)

    await repo.upsert_input(session, item.id, user.id, content)
    await session.commit()
    await session.refresh(item)
    return item


async def generate(session: AsyncSession, couple: Couple, session_id: int) -> InquirySession:
    """调用一次大模型，生成中立汇总。

    降级策略：
    AI 不可用时回滚事务、保持 collecting 状态，
    双方已经写好的内容不会丢，稍后可以重试。
    """
    item = await _get(session, couple, session_id)
    if item.status != "collecting":
        raise AppError("这个询问已经生成过了", code=13002, status_code=409)

    inputs = await repo.list_inputs(session, item.id)
    if len(inputs) < 2:
        raise AppError("双方都写完之后才能生成", code=13003, status_code=409)

    # 先标记处理中，避免并发重复触发
    item.status = "ai_processing"
    await session.flush()

    prompt = (
        f"问题：{item.question}\n\n"
        + "\n\n".join(f"想法 {i + 1}：{x.content}" for i, x in enumerate(inputs))
    )
    try:
        response = await ai_client.complete(system=SYSTEM_PROMPT, user=prompt)
    except AppError as exc:
        if exc.code in _AI_UNAVAILABLE:
            # 降级：双方的想法已经存下来了，回到 collecting 允许稍后重试
            await session.rollback()
            raise AppError(
                "AI 分析暂时不可用，双方的想法已经保存，稍后再试",
                code=13007,
                status_code=503,
            ) from exc
        raise

    item.ai_response = response
    item.status = "reviewing"
    await session.commit()
    await session.refresh(item)
    return item


async def supplement(
    session: AsyncSession, couple: Couple, user: User, session_id: int, content: str
) -> InquirySession:
    """在 AI 回复之后补充意见。只在 reviewing 阶段允许。"""
    item = await _get(session, couple, session_id)
    if item.status != "reviewing":
        raise AppError("现在还不能补充意见", code=13004, status_code=409)

    await repo.add_supplement(session, item.id, user.id, content)
    await session.commit()
    await session.refresh(item)
    return item


async def close(session: AsyncSession, couple: Couple, session_id: int) -> InquirySession:
    """关闭询问，形成最终记录。"""
    item = await _get(session, couple, session_id)
    if item.status != "reviewing":
        raise AppError("当前状态不能关闭", code=13005, status_code=409)

    item.status = "closed"
    item.closed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return item


async def get_detail(
    session: AsyncSession, couple: Couple, user: User, session_id: int
) -> InquiryOut:
    """查看询问详情。

    匿名性由这里保证：
    - 只返回内容，不返回 user_id
    - 双方都提交之前，inputs 一律为空
    """
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
    """取出属于当前关系的询问，否则 404。"""
    item = await repo.get_session(session, session_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("询问不存在", code=13006, status_code=404)
    return item
