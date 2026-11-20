"""add couple start_date

Revision ID: b2d3f4a5c6d7
Revises: f1a2c3e5b8d4
Create Date: 2026-11-09

「在一起」的起始日单独存一列：绑定动作的时间往往不是真正的相识日。
允许为空，为空时按 bind_at 的日期兜底，因此不需要回填历史数据。
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d3f4a5c6d7'
down_revision: str | None = 'f1a2c3e5b8d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('couples', sa.Column('start_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('couples', 'start_date')
