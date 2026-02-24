import re
import tempfile
import os

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.enums.content_type import ContentType
from keyboards.keyboards import get_cancel_kb, get_accept_registration_admin_kb
from config import ADMIN_CHAT_ID
from database.db import registration_clicked, add_registration_click, update_user_email

reg_router = Router()


class Registration(StatesGroup):
    photo = State()
    name = State()
    surname = State()
    email = State()


@reg_router.callback_query(F.data == "registration")
async def start_registration(call: CallbackQuery, state: FSMContext):
    if not registration_clicked(call.from_user.id):
        await call.message.edit_caption(
            caption="Отправьте фотографию из личного кабинета МФТИ (с фото, именем и фамилией)",
            reply_markup=get_cancel_kb()
        )
        await state.set_state(Registration.photo)
    else:
        await call.message.edit_caption(caption="Ваша заявка на рассмотрении администратора")


@reg_router.message(Registration.photo)
async def ask_name(message: Message, state: FSMContext):
    if message.content_type != ContentType.PHOTO:
        await message.answer("Неверный формат! Отправьте фото!", reply_markup=get_cancel_kb())
        return
    # Сохраняем file_id вместо скачивания файла
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await state.set_state(Registration.name)
    await message.answer("Введите имя:")


@reg_router.message(Registration.name)
async def ask_surname(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.surname)
    await message.answer("Введите фамилию:")


@reg_router.message(Registration.surname)
async def ask_email(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    await state.update_data(surname=message.text.strip())
    await state.set_state(Registration.email)
    await message.answer("Введите ваш email (нужен для входа в Mini App):")


@reg_router.message(Registration.email)
async def process_email(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Введите email текстом!", reply_markup=get_cancel_kb())
        return

    email = message.text.strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await message.answer("Неверный формат email. Попробуйте ещё раз:")
        return

    data = await state.update_data(email=email)
    await send_to_admin(message, data)
    await state.clear()


async def send_to_admin(message: Message, data: dict):
    await message.bot.send_photo(
        ADMIN_CHAT_ID,
        photo=data["photo"],
        caption=f'Пользователь: {data["name"]} {data["surname"]}\nEmail: {data["email"]}',
        reply_markup=get_accept_registration_admin_kb(message.chat.id, data["name"], data["surname"])
        # email убрали из клавиатуры — берём из caption при одобрении
    )
    add_registration_click(message.from_user.id)
    await message.answer("Заявка отправлена на рассмотрение администратора!")