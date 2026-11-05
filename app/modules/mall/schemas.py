"""商城模块的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    """上架商品。提交后进入待审批状态，对方确认价格后才真正上架。"""

    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price_coins: int = Field(gt=0, le=100_000)
    # 可兑换次数，None 表示不限
    max_orders: int | None = Field(default=None, ge=1, le=1000)


class ItemApprove(BaseModel):
    """审批通过。price_coins 不传则沿用创建者的建议价。"""

    price_coins: int | None = Field(default=None, gt=0, le=100_000)


class ItemReject(BaseModel):
    """拒绝上架。"""

    reason: str | None = Field(default=None, max_length=200)


class ItemOut(BaseModel):
    """商品信息。同时暴露建议价和最终价，前端可展示“议价”过程。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    title: str
    description: str | None
    price_coins: int
    approved_price: int | None
    max_orders: int | None
    status: str
    reject_reason: str | None
    created_at: datetime


class OrderCreate(BaseModel):
    """购买请求。只需要商品 id，价格由服务端决定。"""

    item_id: int


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
