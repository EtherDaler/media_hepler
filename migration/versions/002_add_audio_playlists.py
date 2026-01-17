"""Add audio, playlists, favorites tables for Mini App

Revision ID: 002
Revises: 001
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица аудио файлов пользователей
    op.create_table(
        'user_audio',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('file_id', sa.String(length=255), nullable=False),
        sa.Column('file_unique_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('artist', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.BigInteger(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_audio_id'), 'user_audio', ['id'], unique=False)
    op.create_index(op.f('ix_user_audio_user_id'), 'user_audio', ['user_id'], unique=False)
    op.create_index('ix_user_audio_file_id', 'user_audio', ['file_id'], unique=False)

    # Таблица плейлистов
    op.create_table(
        'playlists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('cover_file_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_playlists_id'), 'playlists', ['id'], unique=False)
    op.create_index(op.f('ix_playlists_user_id'), 'playlists', ['user_id'], unique=False)

    # Таблица треков в плейлистах
    op.create_table(
        'playlist_tracks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=False),
        sa.Column('audio_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['audio_id'], ['user_audio.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('playlist_id', 'audio_id', name='uq_playlist_audio')
    )
    op.create_index(op.f('ix_playlist_tracks_id'), 'playlist_tracks', ['id'], unique=False)
    op.create_index('ix_playlist_tracks_playlist_id', 'playlist_tracks', ['playlist_id'], unique=False)

    # Таблица избранного
    op.create_table(
        'favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('audio_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['audio_id'], ['user_audio.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'audio_id', name='uq_user_audio_favorite')
    )
    op.create_index(op.f('ix_favorites_id'), 'favorites', ['id'], unique=False)
    op.create_index(op.f('ix_favorites_user_id'), 'favorites', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('uq_user_audio_favorite', 'favorites', type_='unique')
    op.drop_index(op.f('ix_favorites_user_id'), table_name='favorites')
    op.drop_index(op.f('ix_favorites_id'), table_name='favorites')
    op.drop_table('favorites')
    
    op.drop_constraint('uq_playlist_audio', 'playlist_tracks', type_='unique')
    op.drop_index('ix_playlist_tracks_playlist_id', table_name='playlist_tracks')
    op.drop_index(op.f('ix_playlist_tracks_id'), table_name='playlist_tracks')
    op.drop_table('playlist_tracks')
    
    op.drop_index(op.f('ix_playlists_user_id'), table_name='playlists')
    op.drop_index(op.f('ix_playlists_id'), table_name='playlists')
    op.drop_table('playlists')
    
    op.drop_index('ix_user_audio_file_id', table_name='user_audio')
    op.drop_index(op.f('ix_user_audio_user_id'), table_name='user_audio')
    op.drop_index(op.f('ix_user_audio_id'), table_name='user_audio')
    op.drop_table('user_audio')

