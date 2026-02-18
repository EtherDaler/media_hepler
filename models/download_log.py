from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, Index
from sqlalchemy.sql import func
from .base import Base


class DownloadLog(Base):
    __tablename__ = 'download_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    type = Column(String(20), nullable=False)  # audio, youtube, shorts, reels, tiktok, pinterest
    link = Column(String(2048), nullable=True)
    status = Column(Boolean, default=True)  # True = успех, False = ошибка
    datetime = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_download_logs_user_id', 'user_id'),
        Index('ix_download_logs_type', 'type'),
        Index('ix_download_logs_datetime', 'datetime'),
        Index('ix_download_logs_user_type_date', 'user_id', 'type', 'datetime'),
    )
