from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from keyboards.laundry_keyboards import record_set_day_kb, record_set_machine_kb, record_set_time_kb, cart_kb
from keyboards.keyboards import get_cancel_kb, get_start_kb
from services.laundry.schedule import Schedule
from services.laundry.plot_schedule import plot_schedule
from datetime import datetime
from database.db import is_registered, User
import random
import string
import os
from config import LAUNDRY_DATA_PATH as SCHEDULE_PATH
laundry_router = Router()

SCHEDULE_PATH = os.getenv("LAUNDRY_DATA_PATH")

class RecordInfo(StatesGroup):
    date = State()
    machine = State()
    manual_time = State()
    exit_state = State()
    all_laundries = State()
    original_message = State()
    filepath = State()

@laundry_router.callback_query(lambda callback : callback.data in ["laundry_record","exit_from_record"])
async def start_record(call : CallbackQuery, state : FSMContext):
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Выберите день: "), reply_markup=record_set_day_kb(datetime.today()))
    await state.update_data(all_laundries = [])
    await state.set_state(RecordInfo.date)

    
@laundry_router.callback_query(F.data.contains("record_date"))
async def set_day(call : CallbackQuery, state : FSMContext):
    date = call.data.split()[1]
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    filepath = 'tmp_files/' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) + ".png"
    plot_schedule(schedule=schedule.schedule, date=date, filepath=filepath)
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile(filepath), caption="Выберите машинку: "), reply_markup=record_set_machine_kb())
    await state.update_data(date = date)
    await state.update_data(filepath=filepath)
    await state.update_data(original_message = call.message)
    await state.set_state(RecordInfo.machine)

@laundry_router.callback_query(F.data.contains("Машинка"))
async def set_machine(call : CallbackQuery, state : FSMContext):
    machine = call.data.split()[1]
    if machine in ["4", "5"]:
        return
    data = await state.update_data(machine=machine)
    try: 
        os.remove(data["filepath"])
    except Exception:
        pass
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    await call.message.edit_caption(caption=f"Выберите время:", reply_markup=record_set_time_kb(schedule, data["date"], data["machine"]))
    
@laundry_router.callback_query(F.data.contains("set_time"))
async def set_time(call : CallbackQuery, state : FSMContext):
    _, begin_time, end_time = call.data.split()
    data = await state.get_data()
    #schedule = Schedule(SCHEDULE_PATH)
    #schedule.load_schedule()
    #user = is_registered(call.message.chat.id)
    data["all_laundries"].append((data["machine"], begin_time, end_time))
    #schedule.add_booking(data["date"], data["machine"], begin_time, end_time, label = f"{user.surname} {user.name[0]}.")
    await state.update_data(all_laundries = data["all_laundries"])
    await cart_view(call.message, state)

@laundry_router.callback_query(F.data == "manual_time")
async def receive_manual_time(call : CallbackQuery, state : FSMContext):
    await state.set_state(RecordInfo.manual_time)
    await call.message.edit_caption(caption="Введите ваше время в формате чч:мм-чч:мм (например, 09:00-10:00)", reply_markup=get_cancel_kb())

@laundry_router.message(RecordInfo.manual_time)
async def send_manual_time(message : Message, state : FSMContext):
    try:
        begin_time, end_time = message.text.split("-")
        datetime.strptime(begin_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
        schedule = Schedule(SCHEDULE_PATH)
        schedule.load_schedule()
        data = await state.get_data()
        if schedule.is_time_available(data["date"], data["machine"], begin_time, end_time):
            #schedule.add_booking(data["date"], data["machine"], begin_time, end_time, f"{user.surname} {user.name[0]}.")
            data["all_laundries"].append((data["machine"], begin_time, end_time))
            data = await state.update_data(all_laundries = data["all_laundries"])
            await cart_view(data["original_message"], state)
            return
        await data["original_message"].edit_caption(caption = "На это время нельзя записаться!!! Введите другое время", reply_markup=record_set_time_kb(schedule, data["date"], data["machine"]))
    except Exception as e:
        print(e)
        await state.set_state(RecordInfo.manual_time)
        await data["original_message"].edit_caption(caption="Неверный формат ввода!!! Попробуйте ещё раз", reply_markup=record_set_time_kb(schedule, data["date"], data["machine"]))

async def cart_view(message : Message, state : FSMContext):
    data = await state.get_data()
    msg_text = "Итого:\n"
    for record in data["all_laundries"]:
        msg_text += f"- Машинка {record[0]}: {record[1]}-{record[2]}\n"
    await message.edit_caption(caption = msg_text, reply_markup=cart_kb(data["date"]))
    
@laundry_router.callback_query(F.data == "laundry_pay")
async def laundry_pay(call : CallbackQuery, state : FSMContext):
    data = await state.get_data()
    user = is_registered(call.message.chat.id)
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    print(data["all_laundries"])
    for record in data["all_laundries"]:
        schedule.add_booking(data["date"], record[0], record[1], record[2], f"{user.surname} {user.name[0]}.")
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Оплата проведена успешно!"), reply_markup=get_start_kb())
    