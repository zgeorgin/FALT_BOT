from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums.content_type import ContentType
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from keyboards.keyboards import get_cancel_kb, get_accept_studyroom_record_admin_kb
from config import ADMIN_CHAT_ID
from database.db import is_registered


sr_router = Router()


class ReserveSR(StatesGroup):
    date = State()
    comment = State()


@sr_router.callback_query(F.data.contains("studyroom_record"))
async def start_record(call: CallbackQuery, state: FSMContext):
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Напишите дату и промежуток времени бронирования в формате 'ПН ДД.ММ ЧЧ:ММ - ЧЧ:ММ'"))
    await state.set_state(ReserveSR.date)


@sr_router.message(ReserveSR.date)
async def ask_date(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат данных! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    await state.update_data(date=message.text)
    await state.set_state(ReserveSR.comment)
    await message.answer("Напишите комментарий(зачем бронируете, что будете делать, сколько людей будет и т.д.)")


@sr_router.message(ReserveSR.comment)
async def ask_comment(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат данных! Отправьте текст!", reply_markup=get_cancel_kb())
        return
    data = await state.update_data(comment=message.text)
    await send_to_admin(message, data)


async def send_to_admin(message: Message, data: dict):
    user = is_registered(message.from_user.id)
    await message.bot.send_message(
        ADMIN_CHAT_ID,
        text=
        f"<b>Пользователь</b>: {user.name}  {user.surname}\n"
        f"<b>Дата</b>: {data['date']}\n"
        f"<b>Комментарий</b>: <i>{data['comment']}</i>",
        reply_markup=get_accept_studyroom_record_admin_kb(message.chat.id),
        parse_mode="html"
    )
