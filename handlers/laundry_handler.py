from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.keyboards import record_set_day_kb

laundry_router = Router()

@laundry_router.callback_query(F.data == "laundry_record")
async def start_record(call : CallbackQuery):
    call.message.edit_text(text="Выберите день: ", reply_markup=)