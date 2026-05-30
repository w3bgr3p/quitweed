import os
from dataclasses import dataclass


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/quitbot")
    REPORTS_THRESHOLD: int = 3  # сколько жалоб чтобы скрыть заметку
    NOTES_WINDOW_DAYS: int = 2  # показывать заметки с ±N дней
    NOTES_PER_REQUEST: int = 5  # сколько чужих заметок показывать за раз
