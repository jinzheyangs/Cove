"""商城模块的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    """上架商品。提交后直接上架，无需对方审批。"""

    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price_coins: int = Field(gt=0, le=100_000)
    # 可兑换次数，None 表示不限
    max_orders: int | None = Field(default=None, ge=1, le=1000)


class ItemOut(BaseModel):
    """商品信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    title: str
    description: str | None
    price_coins: int
    max_orders: int | None
    status: str
    created_at: datetime


class OrderCreate(BaseModel):
    """购买请求。价格由服务端决定。

    idempotency_key 由客户端生成，防止网络重试导致重复扣币。
    """

    item_id: int
    idempotency_key: str | None = Field(default=None, max_length=64)


class OrderOut(BaseModel):
    """订单。price 是下单时的成交价快照。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    buyer_id: int
    price: int
    status: str
    completed_at: datetime | None
    created_at: datetime
