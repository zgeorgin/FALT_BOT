from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from keyboards.keyboards import get_cancel_kb
reg_router = Router()

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
    file_path = "photo.jpg"
    
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
    await summarize_info(message, data)
    
async def summarize_info(message : Message, data : dict):
    await message.answer_photo(FSInputFile(data["photo"]))
    await message.answer(data["name"])
    
