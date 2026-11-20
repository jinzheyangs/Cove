"""remove mall approval flow

取消商品审批：上架即 approved，删除 approver_id / reject_reason / approved_price，
status 只保留 approved / offline，默认值改为 approved。

Revision ID: a7c3e9f2d1b4
Revises: 23d1f11bfa6d
Create Date: 2026-11-09 15:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e9f2d1b4'
down_revision: str | None = '23d1f11bfa6d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 存量待审批 / 被拒绝的商品直接转为已上架
    op.execute(
        "UPDATE mall_items SET status = 'approved' "
        "WHERE status IN ('pending', 'rejected')"
    )

    # 2. 替换状态 CHECK 约束：只允许 approved / offline
    op.drop_constraint('ck_mall_items_status', 'mall_items', type_='check')
    op.create_check_constraint(
        'ck_mall_items_status',
        'mall_items',
        "status IN ('approved', 'offline')",
    )

    # 3. 状态列默认值改为 approved
    op.alter_column(
        'mall_items',
        'status',
        existing_type=sa.String(length=20),
        server_default='approved',
        existing_nullable=False,
    )

    # 4. 删除审批相关字段（approver_id 带外键，drop_column 会一并移除其外键）
    op.drop_column('mall_items', 'approver_id')
    op.drop_column('mall_items', 'reject_reason')
    op.drop_column('mall_items', 'approved_price')


def downgrade() -> None:
    # 1. 加回审批相关字段
    op.add_column(
        'mall_items',
        sa.Column('approved_price', sa.BigInteger(), nullable=True),
    )
    op.add_column(
        'mall_items',
        sa.Column('reject_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'mall_items',
        sa.Column(
            'approver_id',
            sa.BigInteger(),
            sa.ForeignKey('users.id'),
            nullable=True,
        ),
    )
    # 回填 approved_price，保持旧版本的成交取值可用
    op.execute("UPDATE mall_items SET approved_price = price_coins")

    # 2. 状态列默认值改回 pending
    op.alter_column(
        'mall_items',
        'status',
        existing_type=sa.String(length=20),
        server_default='pending',
        existing_nullable=False,
    )

    # 3. 恢复旧的状态 CHECK 约束
    op.drop_constraint('ck_mall_items_status', 'mall_items', type_='check')
    op.create_check_constraint(
        'ck_mall_items_status',
        'mall_items',
        "status IN ('pending', 'approved', 'rejected', 'offline')",
    )
