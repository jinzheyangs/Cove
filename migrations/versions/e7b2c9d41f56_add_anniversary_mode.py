"""add anniversary mode

同一个日子有两种读法：
- countdown 数「还有几天到下一次」：生日、周年庆、未来的一次性事件
- elapsed 数「从那天起已经多少天」：在一起、结婚这类「起点」

Revision ID: e7b2c9d41f56
Revises: c4d19f83ab27
Create Date: 2026-11-10 15:20:41.882014

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b2c9d41f56'
down_revision: str | None = 'c4d19f83ab27'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'anniversaries',
        sa.Column('mode', sa.String(length=16), server_default='countdown', nullable=False),
    )
    # 已经存量的结婚纪念日，本来就该按「已经多少天」读
    op.execute("UPDATE anniversaries SET mode='elapsed' WHERE kind='wedding'")


def downgrade() -> None:
    op.drop_column('anniversaries', 'mode')
