from sqlalchemy import Column, Integer, String, BigInteger, Date, Boolean, TIMESTAMP
from .base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    tg_id = Column(BigInteger, unique=True)
    is_admin = Column(Boolean, default=False)
    datetime_register = Column(TIMESTAMP, nullable=True)