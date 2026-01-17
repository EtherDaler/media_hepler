from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class UserAudio(Base):
    """Метаданные аудио файлов пользователей"""
    __tablename__ = 'user_audio'
    __table_args__ = (
        Index('ix_user_audio_file_id', 'file_id'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    
    # Telegram file identifiers
    file_id = Column(String(255), nullable=False)  # Постоянный file_id для бота
    file_unique_id = Column(String(255), nullable=True)  # Уникальный ID файла
    
    # Метаданные трека
    title = Column(String(255), nullable=True)  # Название трека
    artist = Column(String(255), nullable=True)  # Исполнитель
    duration = Column(Integer, nullable=True)  # Длительность в секундах
    
    # Связь с оригинальным сообщением
    message_id = Column(BigInteger, nullable=True)  # ID сообщения в чате
    
    # Источник
    source = Column(String(50), nullable=True)  # 'youtube', 'soundcloud', etc.
    source_url = Column(Text, nullable=True)  # Оригинальная ссылка
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    playlist_tracks = relationship("PlaylistTrack", back_populates="audio", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="audio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserAudio(id={self.id}, title='{self.title}', artist='{self.artist}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

