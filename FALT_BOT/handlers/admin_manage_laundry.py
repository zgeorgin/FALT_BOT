from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_CHAT_ID
from database.db import get_machine_status
import database.db as db
from keyboards.admin_manage_laundry_keyboards import get_machines_kb, get_actions_with_machines_kb

manage_laundry_router = Router()


@manage_laundry_router.message(Command("manage_laundry"))
async def manage_laundry(message: Message):
    if str(message.chat.id) == ADMIN_CHAT_ID:
        await message.answer("Выберите машинку:", reply_markup=get_machines_kb())


@manage_laundry_router.callback_query(F.data == "exit_from_manage_machines")
async def exit_from_manage_machines(cb: CallbackQuery):
    await cb.message.delete()


@manage_laundry_router.callback_query(F.data.startswith('machine_settings'))
async def machine_settings(cb: CallbackQuery):
    machine_name = cb.data.split(maxsplit=1)[1]
    await cb.message.edit_text(text=f"<i>Машинка</i>: <strong>{machine_name}</strong>\n"
                                    f"<i>Статус</i>: <strong>{'Не работает' if not get_machine_status(machine_name) else 'Работает'}</strong>",
                               parse_mode="html",
                               reply_markup=get_actions_with_machines_kb(machine_name)
                               )


@manage_laundry_router.callback_query(F.data.contains("change_machine_status"))
async def change_machine_status(cb: CallbackQuery):
    machine_name = cb.data.split(maxsplit=1)[1]
    db.change_machine_status(machine_name)
    await cb.message.edit_text(text=f"Статус машинки <strong>{machine_name}</strong> изменен на <strong>'{'Работает' if get_machine_status(machine_name) else 'Не работает'}'</strong>",
                               parse_mode="html"
                               )


@manage_laundry_router.callback_query(F.data == "exit_from_machine_settings")
async def exit_from_machine_settings(cb: CallbackQuery):
    await cb.message.edit_text(text="Выберите машинку:", reply_markup=get_machines_kb())
