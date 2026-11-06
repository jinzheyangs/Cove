"""写接口幂等：同一个 key 重复提交只生效一次。"""

from decimal import Decimal

from sqlalchemy import func, select

from app.modules.bills import service as bill_service
from app.modules.bills.models import Bill
from app.modules.bills.schemas import BillCreate
from app.modules.coins import repository as coin_repo
from app.modules.diaries import service as diary_service
from app.modules.diaries.models import Diary
from app.modules.diaries.schemas import DiaryCreate
from app.modules.mall import service as mall_service
from app.modules.mall.models import MallOrder
from app.modules.mall.schemas import ItemCreate
from app.modules.todos import service as todo_service
from app.modules.todos.models import TodoItem
from app.modules.todos.schemas import TodoCreate
from tests.helpers import fund_user, seed_couple


async def test_diary_same_key_creates_once(session):
    a, _, couple = await seed_couple(session)

    first = await diary_service.create(
        session, couple, a, DiaryCreate(content="今天", idempotency_key="diary-1")
    )
    second = await diary_service.create(
        session, couple, a, DiaryCreate(content="今天", idempotency_key="diary-1")
    )

    assert first.id == second.id
    count = await session.scalar(select(func.count()).select_from(Diary))
    assert count == 1


async def test_todo_same_key_creates_once(session):
    a, _, couple = await seed_couple(session)

    first = await todo_service.create(
        session,
        couple,
        a,
        TodoCreate(category="想去的地方", title="看海", idempotency_key="todo-1"),
    )
    second = await todo_service.create(
        session,
        couple,
        a,
        TodoCreate(category="想去的地方", title="看海", idempotency_key="todo-1"),
    )

    assert first.id == second.id
    count = await session.scalar(select(func.count()).select_from(TodoItem))
    assert count == 1


async def test_bill_same_key_creates_once(session):
    a, _, couple = await seed_couple(session)

    first = await bill_service.create(
        session,
        couple,
        a,
        BillCreate(
            amount=Decimal("10"),
            category="吃饭",
            idempotency_key="bill-1",
        ),
    )
    second = await bill_service.create(
        session,
        couple,
        a,
        BillCreate(
            amount=Decimal("10"),
            category="吃饭",
            idempotency_key="bill-1",
        ),
    )

    assert first.id == second.id
    count = await session.scalar(select(func.count()).select_from(Bill))
    assert count == 1


async def test_mall_same_key_charges_once(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, a, 100)

    item = await mall_service.create_item(
        session, couple, b, ItemCreate(title="早餐", price_coins=10)
    )
    await mall_service.approve_item(session, couple, a, item.id)

    first = await mall_service.buy(
        session, couple, a, item.id, idempotency_key="order-1"
    )
    second = await mall_service.buy(
        session, couple, a, item.id, idempotency_key="order-1"
    )

    assert first.id == second.id
    assert await coin_repo.get_balance(session, a.id) == 90

    count = await session.scalar(select(func.count()).select_from(MallOrder))
    assert count == 1


async def test_without_key_allows_duplicates(session):
    a, _, couple = await seed_couple(session)

    await diary_service.create(session, couple, a, DiaryCreate(content="同一句"))
    await diary_service.create(session, couple, a, DiaryCreate(content="同一句"))

    count = await session.scalar(select(func.count()).select_from(Diary))
    assert count == 2
