"""add created_by to couples

谁发起这段关系（生成邀请码的人）。用途很具体：绑定完成后，只有发起人
需要被引导去填「在一起的那天」，被邀请的人不用再填一遍 —— 日期是共享的，
两个人各弹一次只是重复打扰。

老数据没有这个信息（列为 NULL），前端遇到 NULL 时按原行为处理。

Revision ID: d1e2f3a4b5c6
Revises: c8a1d4e70f52
Create Date: 2026-11-13 11:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: str | None = 'c8a1d4e70f52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('couples', sa.Column('created_by', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'couples_created_by_fkey', 'couples', 'users', ['created_by'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('couples_created_by_fkey', 'couples', type_='foreignkey')
    op.drop_column('couples', 'created_by')
