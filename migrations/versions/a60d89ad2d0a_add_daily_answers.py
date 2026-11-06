"""add daily answers

Revision ID: a60d89ad2d0a
Revises: 584c6720f98a
Create Date: 2026-11-04 21:25:34.311743

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a60d89ad2d0a'
down_revision: str | None = '584c6720f98a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('daily_answers',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('couple_id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('question', sa.String(length=200), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('couple_id', 'user_id', 'day', name='uq_daily_couple_user_day')
    )
    op.create_index('ix_daily_answers_day', 'daily_answers', ['couple_id', 'day'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_daily_answers_day', table_name='daily_answers')
    op.drop_table('daily_answers')
