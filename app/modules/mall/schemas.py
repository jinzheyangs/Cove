from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price_coins: int = Field(gt=0, le=100_000)
    # 可兑换次数，None 表示不限
    max_orders: int | None = Field(default=None, ge=1, le=1000)


class ItemApprove(BaseModel):
    price_coins: int | None = Field(default=None, gt=0, le=100_000)


class ItemReject(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class ItemOut(BaseModel):
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
    item_id: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    buyer_id: int
    price: int
    status: str
    completed_at: datetime | None
    created_at: datetime
