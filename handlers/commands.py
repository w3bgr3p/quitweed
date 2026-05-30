from datetime import date, timezone, timedelta, datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy import select

from db.database import get_session, User
from content_loader import get_content_for_day

router = Router()

TIMELINE_TEXT = """*Этапы отмены каннабиса*

*Дни 1–3 — Острая фаза*
CB1-рецепторы в дефиците, норадреналин без тормоза. Беспокойство, невозможность сосредоточиться, раздражительность.

*Дни 4–7 — Пик дискомфорта*
Дофаминовый минимум. Ангедония, плохой сон (REM rebound), настроение на дне. Физиологически худшая неделя.

*Дни 8–14 — Стабилизация*
Острая фаза позади. CB1-рецепторы восстановлены на 50–70%. Появляются хорошие часы. Начинается нейрогенез гиппокампа.

*Дни 15–30 — Психологическая фаза*
Физическая отмена завершена. Тяжёлая дисфория, апатия, потеря смысла — у части людей до клинической депрессии. Триггеры опасны. Здесь большинство срывов.

*Дни 31–60 — Когнитивное восстановление*
CB1 восстановлены на 80–90%. Исполнительные функции возвращаются. Окна ясности. Главный триггер — стресс.

*Дни 61–90 — Нормализация*
CB1 восстановлены полностью. Сон норма. Тяга ситуативная, не фоновая.

*День 90+ — Долгосрочная адаптация*
Эндоканнабиноидная система восстановлена. Трезвое состояние — базовое."""


def today_for_offset(utc_offset: int) -> date:
    tz = timezone(timedelta(hours=utc_offset))
    return datetime.now(tz).date()


class ResetStates(StatesGroup):
    waiting_confirm = State()
    waiting_new_date = State()


@router.message(lambda m: m.text == "/status")
async def cmd_status(message: Message):
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
    content = get_content_for_day(day)
    period_title = content["title"] if content else "—"

    await message.answer(
        f"*День {day}*\n"
        f"Период: {period_title}\n"
        f"Дата начала: {user.quit_date.strftime('%d.%m.%Y')}\n"
        f"Ежедневное сообщение: {user.morning_time.strftime('%H:%M')} (UTC{user.utc_offset:+d})",
        parse_mode="Markdown"
    )


@router.message(lambda m: m.text == "/timeline")
async def cmd_timeline(message: Message):
    await message.answer(TIMELINE_TEXT, parse_mode="Markdown")


@router.message(lambda m: m.text == "/reset")
async def cmd_reset(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Сбросить дату и начать заново?", reply_markup=kb)
    await state.set_state(ResetStates.waiting_confirm)


@router.message(ResetStates.waiting_confirm)
async def process_reset_confirm(message: Message, state: FSMContext):
    if message.text.strip().lower() != "да":
        await state.clear()
        await message.answer("Отменено.", reply_markup=ReplyKeyboardRemove())
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Сегодня")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Новая дата начала — ДД.ММ.ГГГГ или *Сегодня*.",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(ResetStates.waiting_new_date)


@router.message(ResetStates.waiting_new_date)
async def process_reset_date(message: Message, state: FSMContext):
    text = message.text.strip()

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await state.clear()
        return

    if text.lower() == "сегодня":
        new_date = today_for_offset(user.utc_offset)
    else:
        try:
            parts = text.split(".")
            new_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            await message.answer("Не понял дату. Формат: ДД.ММ.ГГГГ")
            return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.quit_date = new_date
            await session.commit()

    await state.clear()
    await message.answer(
        f"Дата обновлена: {new_date.strftime('%d.%m.%Y')}. День 1.",
        reply_markup=ReplyKeyboardRemove()
    )
