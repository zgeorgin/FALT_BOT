from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from keyboards.keyboards import get_cancel_kb, get_admin_kb
import os
reg_router = Router()

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
class Registration(StatesGroup):
    photo = State()
    name = State()
    surname = State()

@reg_router.callback_query(F.data == "registration")
async def start_registration(call : CallbackQuery, state : FSMContext):
    await call.message.edit_text("Отправьте фотографию из своего личного кабинета МФТИ, на которой видно вашу фотографию, имя и фамилию", reply_markup=get_cancel_kb())
    await state.set_state(Registration.photo)
    
@reg_router.message(Registration.photo)
async def ask_name(message : Message, state : FSMContext):
    if message.content_type != ContentType.PHOTO:
        await message.answer("Неверный формат данных! Отправьте фото!", reply_markup=get_cancel_kb())
        return
    photo = message.photo[-1]
    file_id = photo.file_id

    file_info = await message.bot.get_file(file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)
    file_path = "tmp_files/photo.jpg"
    
    with open(file_path, "wb") as file:
        file.write(downloaded_file.read())
        
    await state.update_data(photo=file_path)
    await state.set_state(Registration.name)
    await message.answer("Введите имя: ")
    
@reg_router.message(Registration.name)
async def ask_surname(message : Message, state : FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат данных! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    await state.update_data(name=message.text)
    await state.set_state(Registration.surname)
    await message.answer("Введите фамилию: ")
    
@reg_router.message(Registration.surname)
async def send_info(message : Message, state : FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат данных! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    data = await state.update_data(surname=message.text)
    await send_to_admin(message, data)
    
async def send_to_admin(message : Message, data : dict):
    await message.bot.send_photo(ADMIN_CHAT_ID, FSInputFile(data["photo"]), caption=f'Пользователь: {data["name"]} {data["surname"]}', reply_markup=get_admin_kb(message.chat.id, data["name"], data["surname"]))
