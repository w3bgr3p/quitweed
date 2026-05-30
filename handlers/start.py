from datetime import date, time, timezone, timedelta
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy import select

from db.database import get_session, User

router = Router()


class OnboardingStates(StatesGroup):
    waiting_quit_date = State()
    waiting_morning_time = State()
    waiting_utc_offset = State()


def today_for_offset(utc_offset: int) -> date:
    tz = timezone(timedelta(hours=utc_offset))
    from datetime import datetime
    return datetime.now(tz).date()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if user:
        today = today_for_offset(user.utc_offset)
        day = (today - user.quit_date).days + 1
        await message.answer(
            f"Ты уже зарегистрирован. День {day}.\n"
            f"Дата начала: {user.quit_date.strftime('%d.%m.%Y')}\n\n"
            f"Команды: /today /status /timeline /reset"
        )
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Сегодня")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Когда ты бросил?\n\n"
        "Напиши дату в формате ДД.ММ.ГГГГ или нажми *Сегодня*.",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(OnboardingStates.waiting_quit_date)


@router.message(OnboardingStates.waiting_quit_date)
async def process_quit_date(message: Message, state: FSMContext):
    text = message.text.strip()

    # дату пока не можем валидировать без offset — сохраняем как есть
    if text.lower() == "сегодня":
        await state.update_data(quit_date="today")
    else:
        try:
            parts = text.split(".")
            d = date(int(parts[2]), int(parts[1]), int(parts[0]))
            await state.update_data(quit_date=d.isoformat())
        except Exception:
            await message.answer("Не понял дату. Формат: ДД.ММ.ГГГГ")
            return

    common_offsets = ["-8", "-7", "-6", "-5", "-4", "-3", "+1", "+2", "+3", "+5", "+6", "+7", "+8"]
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"UTC{o}") for o in row]
                  for row in [common_offsets[:5], common_offsets[5:]]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Твой часовой пояс?\n\n"
        "Выбери из списка или напиши вручную, например *-5* или *+3*",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(OnboardingStates.waiting_utc_offset)


@router.message(OnboardingStates.waiting_utc_offset)
async def process_utc_offset(message: Message, state: FSMContext):
    text = message.text.strip().replace("UTC", "").replace("utc", "")
    try:
        offset = int(text)
        if offset < -12 or offset > 14:
            raise ValueError
    except Exception:
        await message.answer("Не понял. Напиши число, например -5 или +3")
        return

    await state.update_data(utc_offset=offset)

    await message.answer(
        "В какое время присылать ежедневное сообщение?\n\n"
        "Напиши в формате ЧЧ:ММ, например *08:00*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OnboardingStates.waiting_morning_time)


@router.message(OnboardingStates.waiting_morning_time)
async def process_morning_time(message: Message, state: FSMContext):
    try:
        h, m = map(int, message.text.strip().split(":"))
        morning_time = time(h, m)
    except Exception:
        await message.answer("Не понял время. Формат: ЧЧ:ММ")
        return

    data = await state.get_data()
    utc_offset = data["utc_offset"]

    if data["quit_date"] == "today":
        quit_date = today_for_offset(utc_offset)
    else:
        quit_date = date.fromisoformat(data["quit_date"])

    async with get_session() as session:
        user = User(
            telegram_id=message.from_user.id,
            quit_date=quit_date,
            morning_time=morning_time,
            utc_offset=utc_offset
        )
        session.add(user)
        await session.commit()

    await state.clear()

    day = (today_for_offset(utc_offset) - quit_date).days + 1
    await message.answer(
        f"Готово. День {day}.\n"
        f"Ежедневное сообщение — в {morning_time.strftime('%H:%M')} (UTC{utc_offset:+d}).\n\n"
        f"Напиши /today чтобы получить сообщение прямо сейчас."
    )
