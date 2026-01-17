from sqlalchemy import Column, Integer, BigInteger, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Favorite(Base):
    """Избранные треки пользователей"""
    __tablename__ = 'favorites'
    __table_args__ = (
        UniqueConstraint('user_id', 'audio_id', name='uq_user_audio_favorite'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    audio_id = Column(Integer, ForeignKey('user_audio.id', ondelete='CASCADE'), nullable=False)
    
    # Timestamps
    added_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    audio = relationship("UserAudio", back_populates="favorites")

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, audio_id={self.audio_id})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'audio': self.audio.to_dict() if self.audio else None,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }

