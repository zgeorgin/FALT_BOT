from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import get_main_menu_kb
main_router = Router()

@main_router.message(CommandStart())
async def start_message(message : Message):
    await message.answer('Добро пожаловать в Сервисы ФАЛТ 2.0!', reply_markup=get_main_menu_kb(message.chat.id))

@main_router.callback_query(F.data == "start_from_button")
async def start_message_from_button(call : CallbackQuery):
    await call.message.edit_text('Добро пожаловать в Сервисы ФАЛТ 2.0!', reply_markup=get_main_menu_kb(call.message.chat.id))
    
@main_router.callback_query(F.data == "cancel")
async def cancel_action(call : CallbackQuery):
    await call.message.edit_text('Возвращаюсь в главное меню!')
    await start_message(call.message)
    
@main_router.callback_query(F.data == "support")
async def support(call : CallbackQuery):
    await call.message.edit_text('При возникновении проблем с ботом писать сюда: @zgeorgin', reply_markup=get_main_menu_kb(call.message.chat.id))
    
@main_router.callback_query(F.data == "studyroom_record")
async def support(call : CallbackQuery):
    await call.message.edit_text('Функция бронирования боталки скоро будет добавлена!', reply_markup=get_main_menu_kb(call.message.chat.id))