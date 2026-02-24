from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from aiogram.filters import Command
from keyboards.keyboards import get_start_kb, get_main_menu_kb
from config import ADMIN_CHAT_ID
import os
from database.db import (
    User, add_user, set_registration_click_status, update_user_email,
    is_registered, get_wallet_balance, admin_add_money
)
from sources.generate_file import generate_file

admin_router = Router()


@admin_router.callback_query(F.data.contains("registration_admin_accept"))
async def accepting_registration(call: CallbackQuery):
    data = call.data.split()
    user_id = int(data[0])

    lines = call.message.caption.split("\n")
    name_surname = lines[0].replace("Пользователь: ", "").strip().split()
    name = name_surname[0]
    surname = name_surname[1] if len(name_surname) > 1 else ""
    email = lines[1].replace("Email: ", "").strip() if len(lines) > 1 else ""

    user = User(user_id, name, surname)
    add_user(user)
    update_user_email(user_id, email)

    await call.bot.edit_message_caption(
        message_id=call.message.message_id,
        chat_id=call.message.chat.id,
        caption="Заявка одобрена",
        reply_markup=None
    )
    await call.bot.send_message(user_id, "Вы успешно зарегистрированы!", reply_markup=get_main_menu_kb(user_id))


@admin_router.callback_query(F.data.contains("registration_admin_decline"))
async def declining_registration(call: CallbackQuery):
    data = call.data.split()
    try:
        user_id = int(data[0])
        await call.bot.edit_message_caption(
            message_id=call.message.message_id, 
            chat_id=call.message.chat.id, 
            caption="Заявка отклонена", 
            reply_markup=None
        )
        await call.bot.send_message(user_id, "Ваша заявка на регистрацию отклонена!", reply_markup=get_start_kb())
    except:
        user_id = int(data[0])
        await call.bot.edit_message_caption(
            message_id=call.message.message_id, 
            chat_id=call.message.chat.id, 
            caption="Заявка отклонена", 
            reply_markup=None
        )
        await call.bot.send_message(user_id, "Неправильный формат!!!", reply_markup=get_start_kb())
    set_registration_click_status(user_id)


@admin_router.callback_query(F.data.contains("studyroom_record_admin_decline"))
async def studyroom_decline(call: CallbackQuery):
    user_id = int(call.data.split()[0])
    await call.bot.edit_message_text(
        message_id=call.message.message_id, 
        chat_id=call.message.chat.id, 
        text=f"{call.message.text}\n\nЗаявка отклонена", 
        reply_markup=None
    )
    await call.bot.send_photo(
        user_id, 
        photo=FSInputFile("falt.jpg"), 
        caption="Ваша заявка на бронирование боталки отклонена!", 
        reply_markup=get_start_kb()
    )


@admin_router.callback_query(F.data.contains("studyroom_record_admin_accept"))
async def studyroom_accept(call: CallbackQuery):
    user_id = int(call.data.split()[0])
    await call.bot.edit_message_text(
        message_id=call.message.message_id, 
        chat_id=call.message.chat.id, 
        text=f"{call.message.html_text}\n\nЗаявка одобрена", 
        reply_markup=None, 
        parse_mode="html"
    )
    await call.bot.send_photo(
        user_id, 
        photo=FSInputFile("falt.jpg"), 
        caption="Ваша заявка на бронирование боталки принята!", 
        reply_markup=get_start_kb()
    )

    try:
        path = await generate_file(call.message.text)
        await call.bot.send_document(
            user_id, 
            document=FSInputFile(path), 
            caption="Распечатайте данный файл и повесьте на дверь боталки"
        )
        try:
            os.remove(path)
        except OSError:
            pass
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# КОМАНДА ДОБАВЛЕНИЯ ДЕНЕГ (АДМИН)
# ═══════════════════════════════════════════════════════════════════════════════

@admin_router.message(Command("addmoney"))
async def cmd_add_money(message: Message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /addmoney user_id amount\nПример: /addmoney 123456789 500")
        return
    
    try:
        user_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: /addmoney 123456789 500")
        return
    
    user = is_registered(user_id)
    if not user:
        await message.answer(f"❌ Пользователь {user_id} не найден")
        return
    
    if admin_add_money(user_id, amount):
        new_balance = get_wallet_balance(user_id)
        await message.answer(
            f"✅ Добавлено {amount}₽\n"
            f"Пользователь: {user.name} {user.surname}\n"
            f"Новый баланс: {new_balance}₽"
        )
    else:
        await message.answer("❌ Ошибка добавления денег")