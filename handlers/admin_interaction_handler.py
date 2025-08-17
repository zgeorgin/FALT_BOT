from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from keyboards.keyboards import get_start_kb
from database.db import User, add_user
import os

admin_router = Router()

@admin_router.callback_query(F.data.contains("admin_accept"))
async def accepting_registration(call : CallbackQuery):
    data = call.data.split()
    user_id = data[0]
    name = " ".join(data[1:-2])
    surname = data[-2]
    user = User(user_id, name, surname)
    add_user(user)
    await call.bot.edit_message_caption(message_id=call.message.message_id, chat_id=call.message.chat.id, caption="Заявка одобрена", reply_markup=None)
    await call.bot.send_message(user_id, "Вы были успешно зарегистрированы!", reply_markup=get_start_kb())
    
@admin_router.callback_query(F.data.contains("admin_decline"))
async def declining_registration(call : CallbackQuery):
    try:
        data = call.data.split()
        user_id, name, surname = data[:-1]
        await call.bot.edit_message_caption(message_id=call.message.message_id, chat_id=call.message.chat.id, caption="Заявка отклонена", reply_markup=None)
        await call.bot.send_message(user_id, "Ваша заявка на регистрацию отклонена!", reply_markup=get_start_kb())
    except:
        data = call.data.split()
        user_id = data[0]
        await call.bot.edit_message_caption(message_id=call.message.message_id, chat_id=call.message.chat.id, caption="Заявка отклонена", reply_markup=None)
        await call.bot.send_message(user_id, "Неправильный формат!!!", reply_markup=get_start_kb())
    