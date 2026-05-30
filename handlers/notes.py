import random
from datetime import date
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func, and_

from config import Config
from db.database import get_session, User, Note, Report

router = Router()
config = Config()


class NoteStates(StatesGroup):
    waiting_text = State()


def report_keyboard(note_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚩 Пожаловаться", callback_data=f"report_{note_id}")]
    ])


async def get_user_day(telegram_id: int) -> int | None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
    if not user:
        return None
    return (date.today() - user.quit_date).days + 1


@router.callback_query(F.data == "note_add")
async def cb_note_add(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Напиши заметку. Она будет анонимной.")
    await state.set_state(NoteStates.waiting_text)


@router.message(NoteStates.waiting_text)
async def process_note_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 1000:
        await message.answer("Слишком длинно. Максимум 1000 символов.")
        return

    day = await get_user_day(message.from_user.id)
    if not day:
        await message.answer("Сначала /start")
        await state.clear()
        return

    async with get_session() as session:
        note = Note(day_number=day, text=text)
        session.add(note)
        await session.commit()

    await state.clear()
    await message.answer("Заметка сохранена.")


@router.callback_query(F.data == "note_read")
async def cb_note_read(callback: CallbackQuery):
    await callback.answer()

    day = await get_user_day(callback.from_user.id)
    if not day:
        await callback.message.answer("Сначала /start")
        return

    window = config.NOTES_WINDOW_DAYS
    async with get_session() as session:
        result = await session.execute(
            select(Note).where(
                and_(
                    Note.day_number >= day - window,
                    Note.day_number <= day + window,
                    Note.hidden == False
                )
            )
        )
        notes = result.scalars().all()

    if not notes:
        await callback.message.answer("Пока никто не оставил заметок на этом сроке.")
        return

    sample = random.sample(notes, min(config.NOTES_PER_REQUEST, len(notes)))

    for note in sample:
        text = f"— День {note.day_number}: \"{note.text}\""
        await callback.message.answer(text, reply_markup=report_keyboard(note.id))


@router.callback_query(F.data.startswith("report_"))
async def cb_report(callback: CallbackQuery):
    await callback.answer()
    note_id = int(callback.data.split("_")[1])
    reporter_id = callback.from_user.id

    async with get_session() as session:
        # проверить что не жаловался уже
        existing = await session.execute(
            select(Report).where(
                and_(
                    Report.note_id == note_id,
                    Report.reporter_telegram_id == reporter_id
                )
            )
        )
        if existing.scalar_one_or_none():
            await callback.message.answer("Ты уже жаловался на эту заметку.")
            return

        report = Report(note_id=note_id, reporter_telegram_id=reporter_id)
        session.add(report)

        # обновить счётчик
        note = await session.get(Note, note_id)
        if note:
            note.reports_count += 1
            if note.reports_count >= config.REPORTS_THRESHOLD:
                note.hidden = True

        await session.commit()

    await callback.message.answer("Жалоба принята.")
