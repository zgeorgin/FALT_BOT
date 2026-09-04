from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_machine_names


def get_machines_kb() -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton(text=name, callback_data=f"machine_settings {name}")] for name in get_machine_names()]
    btns.append([InlineKeyboardButton(text="Отмена", callback_data="exit_from_manage_machines")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def get_actions_with_machines_kb(machine_name: str) -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton(text="Изменить статус", callback_data=f"change_machine_status {machine_name}")],
            [InlineKeyboardButton(text="Назад", callback_data=f"exit_from_machine_settings")]]
    return InlineKeyboardMarkup(inline_keyboard=btns)
