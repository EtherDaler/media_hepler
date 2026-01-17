"""Add thumbnail_file_id to user_audio

Revision ID: 003
Revises: 002
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку для хранения file_id обложки из Telegram
    op.add_column(
        'user_audio',
        sa.Column('thumbnail_file_id', sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_audio', 'thumbnail_file_id')

