from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Playlist(Base):
    """Плейлисты пользователей"""
    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    name = Column(String(255), nullable=False)  # Название плейлиста
    description = Column(String(500), nullable=True)  # Описание
    cover_file_id = Column(String(255), nullable=True)  # Обложка плейлиста (file_id)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistTrack.position")

    def __repr__(self):
        return f"<Playlist(id={self.id}, name='{self.name}')>"
    
    def to_dict(self, include_tracks=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'cover_file_id': self.cover_file_id,
            'track_count': len(self.tracks) if self.tracks else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_tracks:
            data['tracks'] = [t.audio.to_dict() for t in self.tracks if t.audio]
        return data


class PlaylistTrack(Base):
    """Треки в плейлистах (связующая таблица)"""
    __tablename__ = 'playlist_tracks'
    __table_args__ = (
        UniqueConstraint('playlist_id', 'audio_id', name='uq_playlist_audio'),
        Index('ix_playlist_tracks_playlist_id', 'playlist_id'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False)
    audio_id = Column(Integer, ForeignKey('user_audio.id', ondelete='CASCADE'), nullable=False)
    position = Column(Integer, nullable=False, default=0)  # Порядок в плейлисте
    
    # Timestamps
    added_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    playlist = relationship("Playlist", back_populates="tracks")
    audio = relationship("UserAudio", back_populates="playlist_tracks")

    def __repr__(self):
        return f"<PlaylistTrack(playlist_id={self.playlist_id}, audio_id={self.audio_id}, position={self.position})>"

