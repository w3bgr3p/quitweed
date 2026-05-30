from datetime import timezone, timedelta, datetime
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from db.database import get_session, User
from content_loader import format_daily_message, format_period_intro, is_first_day_of_period

router = Router()


def today_for_offset(utc_offset: int):
    tz = timezone(timedelta(hours=utc_offset))
    return datetime.now(tz).date()


def daily_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Оставить заметку", callback_data="note_add"),
            InlineKeyboardButton(text="👥 Что писали другие", callback_data="note_read"),
        ]
    ])


async def send_daily(bot, telegram_id: int, day: int):
    # если первый день периода — сначала отправить полный контент периода
    if is_first_day_of_period(day):
        intro = format_period_intro(day)
        if intro:
            await bot.send_message(
                chat_id=telegram_id,
                text=intro,
                parse_mode="Markdown"
            )

    # затем — факт дня
    text = format_daily_message(day)
    await bot.send_message(
        chat_id=telegram_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=daily_keyboard()
    )


@router.message(lambda m: m.text == "/today")
async def cmd_today(message: Message):
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("Сначала /start")
        return

    today = today_for_offset(user.utc_offset)
    day = (today - user.quit_date).days + 1

    if is_first_day_of_period(day):
        intro = format_period_intro(day)
        if intro:
            await message.answer(intro, parse_mode="Markdown")

    text = format_daily_message(day)
    await message.answer(text, parse_mode="Markdown", reply_markup=daily_keyboard())
