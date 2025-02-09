from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import is_registered
from datetime import datetime, timedelta

def record_set_day_kb(date) -> InlineKeyboardMarkup:
    inline_kb_list = [
        InlineKeyboardMarkup(date + timedelta(days=i) for i in range(6))
    ]
    
    return 