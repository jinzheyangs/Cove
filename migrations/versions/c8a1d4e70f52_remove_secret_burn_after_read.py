"""remove burn-after-read from secrets

「阅后即焚」这个可选项下线：规则只剩一条 —— 摘下来看完，这一片就销毁。
所以：
1. 历史中被摘取、还挂着 burned 状态的记录，统一改成 destroyed（内容清空，
   与「读完即销毁」一致；content 为空串时读取端按历史明文兼容，不会解密失败）
2. status 的 check 约束去掉 burned
3. 删掉 is_burn_after_read 列

Revision ID: c8a1d4e70f52
Revises: b3f1c7d9e2a4
Create Date: 2026-11-12 21:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c8a1d4e70f52'
down_revision: str | None = 'b3f1c7d9e2a4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 旧的「已燃尽但内容还留着」的记录，改成已销毁并清空正文
    op.execute(
        "UPDATE secrets SET status = 'destroyed', content = '' WHERE status = 'burned'"
    )

    # 2. 状态约束里去掉 burned
    op.drop_constraint('ck_secrets_status', 'secrets', type_='check')
    op.create_check_constraint(
        'ck_secrets_status', 'secrets', "status IN ('active', 'destroyed')"
    )

    # 3. 不再有「阅后即焚」这个选项
    op.drop_column('secrets', 'is_burn_after_read')


def downgrade() -> None:
    op.add_column(
        'secrets',
        sa.Column(
            'is_burn_after_read', sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.drop_constraint('ck_secrets_status', 'secrets', type_='check')
    op.create_check_constraint(
        'ck_secrets_status', 'secrets', "status IN ('active', 'burned', 'destroyed')"
    )
