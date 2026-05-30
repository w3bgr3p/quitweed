import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from db.database import get_session, User, MessageLog
from handlers.daily import send_daily

logger = logging.getLogger(__name__)


async def dispatch_daily_messages(bot):
    now_utc = datetime.now(timezone.utc)

    async with get_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    for user in users:
        tz = timezone(timedelta(hours=user.utc_offset))
        now_local = now_utc.astimezone(tz)

        if (user.morning_time.hour != now_local.hour or
                user.morning_time.minute != now_local.minute):
            continue

        today = now_local.date()
        day = (today - user.quit_date).days + 1

        async with get_session() as session:
            existing = await session.execute(
                select(MessageLog).where(
                    MessageLog.user_id == user.id,
                    MessageLog.day_number == day
                )
            )
            if existing.scalar_one_or_none():
                continue

            try:
                await send_daily(bot, user.telegram_id, day)
                log = MessageLog(user_id=user.id, day_number=day)
                session.add(log)
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to send to {user.telegram_id}: {e}")


async def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        dispatch_daily_messages,
        trigger=CronTrigger(minute="*"),
        args=[bot],
        id="daily_dispatch"
    )
    scheduler.start()
    logger.info("Scheduler started")
