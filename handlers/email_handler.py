
# handlers/email_handler.py
# Дополнительный обработчик для установки email (для Mini App)

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums.content_type import ContentType
from keyboards.keyboards import get_cancel_kb, get_start_kb
import database.db as db
import re

email_router = Router()

class EmailStates(StatesGroup):
    waiting_email = State()

@email_router.callback_query(F.data == "set_email_prompt")
async def set_email_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_caption(
        caption="Введите ваш email для входа в Mini App:\n"
                "(Этот email будет использоваться для авторизации в веб-приложении)",
        reply_markup=get_cancel_kb()
    )
    await state.set_state(EmailStates.waiting_email)

@email_router.message(EmailStates.waiting_email)
async def process_email(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Пожалуйста, отправьте текстовое сообщение с email.")
        return

    email = message.text.strip().lower()

    # Валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await message.answer(
            "Неверный формат email. Попробуйте еще раз.",
            reply_markup=get_cancel_kb()
        )
        return

    # Проверка, не занят ли email
    existing = db.get_user_by_email(email)
    if existing and existing.user_id != message.from_user.id:
        await message.answer(
            "Этот email уже привязан к другому аккаунту. Используйте другой email.",
            reply_markup=get_cancel_kb()
        )
        return

    # Сохраняем email
    success = db.update_user_email(message.from_user.id, email)
    if success:
        await message.answer(
            f"✅ Email {email} успешно привязан к вашему аккаунту!\n\n"
            f"Теперь вы можете использовать Mini App для бронирования.",
            reply_markup=get_start_kb()
        )
        await state.clear()
    else:
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_kb()
        )
