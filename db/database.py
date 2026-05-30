from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean,
    Date, Time, DateTime, ForeignKey, Text, func
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    quit_date = Column(Date, nullable=False)
    morning_time = Column(Time, nullable=False)  # время отправки ежедневного сообщения
    utc_offset = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now())


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    day_number = Column(Integer, nullable=False)  # день отмены автора в момент записи
    text = Column(Text, nullable=False)
    reports_count = Column(Integer, default=0)
    hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    reporter_telegram_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now())


class MessageLog(Base):
    __tablename__ = "message_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    sent_at = Column(DateTime, default=func.now())


_engine = None
_session_factory = None


async def init_db(database_url: str):
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    return _session_factory()
