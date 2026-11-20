"""add chat memories

Revision ID: b7c2e4f19a63
Revises: d1e2f3a4b5c6
Create Date: 2026-11-13 18:40:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c2e4f19a63'
down_revision: str | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chat_memories',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('couple_id', sa.BigInteger(), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('target_id', sa.BigInteger(), nullable=False),
        sa.Column('conversation_id', sa.BigInteger(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('seq', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'conversation_id', 'day', 'seq', name='uq_chat_memory_conv_day_seq'
        ),
    )
    op.create_index(
        'ix_chat_memory_owner_day', 'chat_memories', ['owner_id', 'day'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_chat_memory_owner_day', table_name='chat_memories')
    op.drop_table('chat_memories')
