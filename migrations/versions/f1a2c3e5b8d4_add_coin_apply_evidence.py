"""add evidence_key to coin_applies

给金币申请（索要金币）增加照片证明字段，存对象存储 key（不存 url）。
照片为选填，所以列可空。

Revision ID: f1a2c3e5b8d4
Revises: a7c3e9f2d1b4
Create Date: 2026-11-09 16:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2c3e5b8d4'
down_revision: str | None = 'a7c3e9f2d1b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'coin_applies',
        sa.Column('evidence_key', sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('coin_applies', 'evidence_key')
