from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from aiogram.types import Message, CallbackQuery
from keyboards.laundry_keyboards import record_set_day_kb, record_set_machine_kb, record_set_time_kb
from keyboards.keyboards import get_cancel_kb
from services.laundry.schedule import Schedule
from services.laundry.plot_schedule import plot_schedule
from datetime import datetime
from database.db import is_registered, User
import os
laundry_router = Router()

SCHEDULE_PATH = os.getenv("LAUNDRY_DATA_PATH")



class RecordInfo(StatesGroup):
    date = State()
    machine = State()
    manual_time = State()
    exit_state = State()

@laundry_router.callback_query(F.data == "laundry_record")
async def start_record(call : CallbackQuery, state : FSMContext):
    await call.message.edit_text(text="Выберите день: ", reply_markup=record_set_day_kb(datetime.today()))
    await state.set_state(RecordInfo.date)
    

@laundry_router.callback_query(F.data.contains("record_date"))
async def set_day(call : CallbackQuery, state : FSMContext):
    date = call.data.split()[1]
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    plot_schedule(schedule=schedule.schedule, date=date, filepath="plot.png")
    await call.bot.send_photo(call.message.chat.id, photo=FSInputFile("plot.png"))
    await state.update_data(date = date)
    await state.set_state(RecordInfo.machine)
    await call.message.edit_text(text="Выберите машинку: ", reply_markup=record_set_machine_kb())

@laundry_router.callback_query(F.data.contains("Машинка"))
async def set_machine(call : CallbackQuery, state : FSMContext):
    machine = call.data.split()[1]
    data = await state.update_data(machine=machine)
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    await call.message.edit_text(text=f"Выберите время:", reply_markup=record_set_time_kb(schedule, data["date"], data["machine"]))
    
@laundry_router.callback_query(F.data.contains("set_time"))
async def set_time(call : CallbackQuery, state : FSMContext):
    _, begin_time, end_time = call.data.split()
    data = await state.get_data()
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    user = is_registered(call.message.chat.id)
    schedule.add_booking(data["date"], data["machine"], begin_time, end_time, label = f"{user.surname} {user.name[0]}.")
    
@laundry_router.callback_query(F.data == "manual_time")
async def receive_manual_time(call : CallbackQuery, state : FSMContext):
    await state.set_state(RecordInfo.manual_time)
    await call.message.edit_text(text="Введите ваше время в формате чч:мм-чч:мм (например, 09:00-10:00)", reply_markup=get_cancel_kb())

@laundry_router.message(RecordInfo.manual_time)
async def send_manual_time(message : Message, state : FSMContext):
    begin_time, end_time = message.text.split("-")
    try:
        datetime.strptime(begin_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
        schedule = Schedule(SCHEDULE_PATH)
        schedule.load_schedule()
        data = await state.get_data()
        user = is_registered(message.chat.id)
        if schedule.is_time_available(data["date"], data["machine"], begin_time, end_time):
            schedule.add_booking(data["date"], data["machine"], begin_time, end_time, f"{user.surname} {user.name[0]}.")
            await message.answer(text="Запись прошла успешно!")
            return
        await message.answer(text = "На это время нельзя записаться!!! Попробуйте ещё раз", reply_markup=None)
    except:
        await state.set_state(RecordInfo.manual_time)
        await message.answer(text="Неверный формат ввода!!! Попробуйте ещё раз", reply_markup=None)

async def cart_view(message : Message):
    message.edit_text()