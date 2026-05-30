import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from db.database import init_db
from handlers import start, daily, notes, commands
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    config = Config()
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await init_db(config.DATABASE_URL)

    dp.include_router(start.router)
    dp.include_router(daily.router)
    dp.include_router(notes.router)
    dp.include_router(commands.router)

    await start_scheduler(bot)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
