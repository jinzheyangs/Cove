"""删除聊天记录导入相关的三张表

模拟Ta 不再支持上传聊天记录，改成「自己聊出来的对话记忆」，
所以导入表、导入消息表和派生的风格画像表一并移除。

Revision ID: d3a7b8c14e52
Revises: b7c2e4f19a63
Create Date: 2026-11-13 19:40:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.core.types


revision: str = 'd3a7b8c14e52'
down_revision: str | None = 'b7c2e4f19a63'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # chat_messages 有指向 chat_imports 的外键，先删子表
    op.drop_index('ix_chat_messages_couple_sender', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_imports_couple', table_name='chat_imports')
    op.drop_table('chat_imports')
    op.drop_table('persona_profiles')


def downgrade() -> None:
    op.create_table('persona_profiles',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('couple_id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('style_summary', app.core.types.EncryptedText(), nullable=True),
    sa.Column('samples_json', app.core.types.EncryptedText(), nullable=True),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('couple_id', 'user_id', name='uq_persona_profile_couple_user')
    )
    op.create_table('chat_imports',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('couple_id', sa.BigInteger(), nullable=False),
    sa.Column('uploaded_by', sa.BigInteger(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('format', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='processing', nullable=False),
    sa.Column('total_messages', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('imported_messages', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('indexed_windows', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('skipped_messages', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('error', app.core.types.EncryptedText(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('processing', 'done', 'failed')", name='ck_chat_import_status'),
    sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_imports_couple', 'chat_imports', ['couple_id', 'created_at'], unique=False)
    op.create_table('chat_messages',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('couple_id', sa.BigInteger(), nullable=False),
    sa.Column('import_id', sa.BigInteger(), nullable=False),
    sa.Column('sender_id', sa.BigInteger(), nullable=True),
    sa.Column('sender_name', sa.String(length=100), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('content', app.core.types.EncryptedText(), nullable=False),
    sa.Column('msg_type', sa.String(length=20), server_default='text', nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
    sa.ForeignKeyConstraint(['import_id'], ['chat_imports.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('couple_id', 'source_hash', name='uq_chat_message_hash')
    )
    op.create_index('ix_chat_messages_couple_sender', 'chat_messages', ['couple_id', 'sender_id', 'sent_at'], unique=False)
