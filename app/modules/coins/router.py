"""金币的 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.coins import service
from app.modules.coins.schemas import BalanceOut, GiftRequest, TransactionItem
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("/balance", response_model=Envelope[BalanceOut])
async def get_balance(user: CurrentUser, session: SessionDep) -> Envelope[BalanceOut]:
    """查询自己的金币余额。没绑定伴侣也可以查。"""
    balance = await service.get_balance(session, user.id)
    return Envelope(data=BalanceOut(balance=balance))


@router.post("/gift", response_model=Envelope[TransactionItem])
async def gift(
    body: GiftRequest,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[TransactionItem]:
    """给对方赠币。

    CurrentCouple 保证已绑定；金币只会发生在两人之间。
    """
    # 回滚会让 ORM 对象过期，先把 id 取出来
    user_id = user.id
    transaction = await service.gift(
        session, couple, user, body.amount, body.remark, body.idempotency_key
    )
    return Envelope(data=service.to_item(transaction, user_id))


@router.get("/transactions", response_model=Envelope[list[TransactionItem]])
async def list_transactions(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[list[TransactionItem]]:
    """分页查询自己的流水。

    结果包含：别人赠给我的、我消费掉的、我赠给别人的。
    """
    transactions = await service.list_transactions(session, user.id, limit, offset)
    return Envelope(data=[service.to_item(tx, user.id) for tx in transactions])
