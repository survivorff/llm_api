"""v2.3 channel key_meta

Revision ID: a1b2c3d4e5f6
Revises: 7481b278d83f
Create Date: 2026-07-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7481b278d83f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('channels', schema=None) as batch_op:
        batch_op.add_column(sa.Column('key_meta', sa.Text(), nullable=True))
    # 兜底：把已存在行的 NULL 初始化为 "{}"
    op.execute("UPDATE channels SET key_meta='{}' WHERE key_meta IS NULL")


def downgrade() -> None:
    with op.batch_alter_table('channels', schema=None) as batch_op:
        batch_op.drop_column('key_meta')
