"""add anniversary kind

结婚纪念日与普通自定义日子共用同一张表，只靠 kind 区分文案与图标：
custom 普通日子 / wedding 结婚纪念日。

Revision ID: c4d19f83ab27
Revises: b2d3f4a5c6d7
Create Date: 2026-11-10 10:12:44.101376

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d19f83ab27'
down_revision: str | None = 'b2d3f4a5c6d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'anniversaries',
        sa.Column('kind', sa.String(length=16), server_default='custom', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('anniversaries', 'kind')
