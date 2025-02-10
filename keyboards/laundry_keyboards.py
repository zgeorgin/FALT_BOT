from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import is_registered
from datetime import datetime, timedelta
from services.laundry.schedule import Schedule

def record_set_day_kb(date) -> InlineKeyboardMarkup:
    inline_kb_list = []
    for i in range(6):
        inline_kb_list.append([InlineKeyboardButton(text = (date + timedelta(days=i)).strftime("%d.%m.%Y"), callback_data=f"record_date {(date + timedelta(days=i)).strftime("%d.%m.%Y")}")])
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def record_set_machine_kb() -> InlineKeyboardMarkup:
    inline_kb_list = []
    for i in range(1, 7):
        inline_kb_list.append([InlineKeyboardButton(text = f"#{i}" if i < 6 else f"#6(Сушилка)", callback_data=f"Машинка {i}")])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def record_set_time_kb(schedule : Schedule, date, machine_id) -> InlineKeyboardMarkup:
    raw_list = []
    normal_date = datetime.strptime(date, "%d.%m.%Y")
    clear_date = datetime(normal_date.year, normal_date.month, normal_date.day, 0, 0, 0)
    for i in range(12):
        begin_time = (clear_date + timedelta(hours = 2 * i)).strftime("%H:%M")
        end_time = (clear_date + timedelta(hours = 2 * (i + 1))).strftime("%H:%M")
        if schedule.is_time_available(date, str(machine_id), begin_time, end_time):
            raw_list.append(InlineKeyboardButton(text=f"{begin_time}-{end_time}",callback_data=f"set_time {begin_time} {end_time}"))
        else:
            raw_list.append(InlineKeyboardButton(text="---", callback_data="missing_time"))
    
    inline_kb_list = []
    for i in range(3):
        inline_kb_list.append([])
        for j in range(4):
            inline_kb_list[-1].append(raw_list[i * 4 + j])
    inline_kb_list.append([InlineKeyboardButton(text="Ввести время вручную", callback_data="manual_time"), InlineKeyboardButton(text="Назад",callback_data="exit_from_record")])
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)