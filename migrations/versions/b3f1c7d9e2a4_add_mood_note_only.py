"""允许每日心情只写一句话、不标情绪

mood 列改为可空：光写字不选心情也是合法的一天。
CHECK 约束 (mood IN (...)) 对 NULL 不生效，所以约束不需要改。

Revision ID: b3f1c7d9e2a4
Revises: e7b2c9d41f56
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "b3f1c7d9e2a4"
down_revision = "e7b2c9d41f56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "mood_records",
        "mood",
        existing_type=sa.String(length=20),
        nullable=True,
    )


def downgrade() -> None:
    # 回退前需要先把已存在的「只有一句话」的记录补上心情，
    # 否则 NOT NULL 会拒绝这些行。
    op.execute("UPDATE mood_records SET mood = 'calm' WHERE mood IS NULL")
    op.alter_column(
        "mood_records",
        "mood",
        existing_type=sa.String(length=20),
        nullable=False,
    )
