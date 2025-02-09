from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import is_registered


def get_main_menu_kb(user_id) -> InlineKeyboardMarkup:
    
    if not is_registered(user_id):
        inline_kb_list = [[InlineKeyboardButton(text="Зарегистрироваться", callback_data="registration")]]
        return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
    
    inline_kb_list = [
        [InlineKeyboardButton(text="Записаться на стирку", callback_data='wash_record')],
        [InlineKeyboardButton(text="Забронировать боталку", callback_data='studyroom_record')],
        [InlineKeyboardButton(text="Тех. поддержка", callback_data='support')]        
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def get_cancel_kb() -> InlineKeyboardMarkup:
    inline_kb_list = [[InlineKeyboardButton(text="Отмена", callback_data="cancel")]]
    
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
    