"""add mood records

Revision ID: 23d1f11bfa6d
Revises: 8447e678c704
Create Date: 2026-11-08 20:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '23d1f11bfa6d'
down_revision: str | None = '8447e678c704'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'mood_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('couple_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('mood', sa.String(length=20), nullable=False),
        sa.Column('level', sa.SmallInteger(), nullable=False),
        # 加密文本底层仍是 TEXT，可空
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('level BETWEEN 1 AND 5', name='ck_mood_level'),
        sa.CheckConstraint("mood IN ('awesome','happy','calm','tired','low')", name='ck_mood_type'),
        sa.ForeignKeyConstraint(['couple_id'], ['couples.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('couple_id', 'user_id', 'day', name='uq_mood_couple_user_day'),
    )
    op.create_index('ix_mood_records_day', 'mood_records', ['couple_id', 'day'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_mood_records_day', table_name='mood_records')
    op.drop_table('mood_records')
