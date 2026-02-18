"""Add download_logs table

Revision ID: 004
Revises: 003
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу для логирования загрузок
    op.create_table(
        'download_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('link', sa.String(length=2048), nullable=True),
        sa.Column('status', sa.Boolean(), default=True),
        sa.Column('datetime', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индексы
    op.create_index('ix_download_logs_user_id', 'download_logs', ['user_id'])
    op.create_index('ix_download_logs_type', 'download_logs', ['type'])
    op.create_index('ix_download_logs_datetime', 'download_logs', ['datetime'])
    op.create_index('ix_download_logs_user_type_date', 'download_logs', ['user_id', 'type', 'datetime'])


def downgrade() -> None:
    op.drop_index('ix_download_logs_user_type_date', table_name='download_logs')
    op.drop_index('ix_download_logs_datetime', table_name='download_logs')
    op.drop_index('ix_download_logs_type', table_name='download_logs')
    op.drop_index('ix_download_logs_user_id', table_name='download_logs')
    op.drop_table('download_logs')
