import math
import os
import tempfile
from datetime import datetime

from aiogram import Router, F
from aiogram.enums.content_type import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile, InputMediaPhoto
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    LAUNDRY_DATA_PATH as SCHEDULE_PATH,
    LAUNDRY_PRICE_PER_HOUR_RUB,
    LAUNDRY_PRICE_PER_HOUR_WASH_RUB,
    LAUNDRY_PRICE_PER_HOUR_DRY_RUB,
)
from database.db import is_registered
from keyboards.keyboards import get_cancel_kb, get_start_kb
from keyboards.laundry_keyboards import record_set_day_kb, record_set_machine_kb, record_set_time_kb, cart_kb
from keyboards.wallet_keyboards import get_insufficient_funds_kb
from services.laundry.plot_schedule import plot_schedule
from services.laundry.schedule import Schedule
from services.wallet.wallet import get_balance, debit_balance, credit_balance


laundry_router = Router()


class RecordInfo(StatesGroup):
    date = State()
    machine = State()
    manual_time = State()
    exit_state = State()
    all_laundries = State()
    original_message = State()
    filepath = State()


def _parse_hourly_rate(default_value: str | None) -> int:
    try:
        if default_value is None:
            return int(round(float(LAUNDRY_PRICE_PER_HOUR_RUB)))
        return int(round(float(default_value)))
    except (TypeError, ValueError):
        return 75


def _rate_for_machine(machine_id: str) -> int:
    try:
        is_dryer = int(machine_id) == 6
    except ValueError:
        is_dryer = False
    if is_dryer:
        return _parse_hourly_rate(LAUNDRY_PRICE_PER_HOUR_DRY_RUB)
    return _parse_hourly_rate(LAUNDRY_PRICE_PER_HOUR_WASH_RUB)


def _hours_for_interval(begin_time: str, end_time: str) -> float:
    start = datetime.strptime(begin_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    minutes = int((end - start).total_seconds() / 60)
    if minutes <= 0:
        raise ValueError("Invalid time interval")
    return minutes / 60


def _amount_for_record(machine_id: str, begin_time: str, end_time: str) -> int:
    hours = _hours_for_interval(begin_time, end_time)
    rate = _rate_for_machine(machine_id)
    return int(round(hours * rate))


def _calc_total_amount(records: list[tuple[str, str, str]]) -> tuple[int, float]:
    total_hours = 0.0
    total_amount = 0
    for machine_id, begin_time, end_time in records:
        hours = _hours_for_interval(begin_time, end_time)
        total_hours += hours
        total_amount += _amount_for_record(machine_id, begin_time, end_time)
    return int(total_amount), total_hours


@laundry_router.callback_query(lambda callback: callback.data in ["laundry_record", "exit_from_record"])
async def start_record(call: CallbackQuery, state: FSMContext):
    await call.message.edit_media(
        InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Выберите день: "),
        reply_markup=record_set_day_kb(datetime.today())
    )
    await state.update_data(all_laundries=[])
    await state.set_state(RecordInfo.date)


@laundry_router.callback_query(F.data.contains("record_date"))
async def set_day(call: CallbackQuery, state: FSMContext):
    date = call.data.split()[1]
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    filepath = tmp.name
    tmp.close()
    plot_schedule(schedule=schedule.schedule, date=date, filepath=filepath)
    await call.message.edit_media(
        InputMediaPhoto(media=FSInputFile(filepath), caption="Выберите машинку: "),
        reply_markup=record_set_machine_kb()
    )
    await state.update_data(date=date)
    await state.update_data(filepath=filepath)
    await state.update_data(original_message=call.message)
    await state.set_state(RecordInfo.machine)


@laundry_router.callback_query(F.data.contains("Машинка"))
async def set_machine(call: CallbackQuery, state: FSMContext):
    machine = call.data.split()[1]
    data = await state.update_data(machine=machine)
    try:
        os.remove(data["filepath"])
    except Exception:
        pass
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    await call.message.edit_caption(
        caption=f"Выберите время:",
        reply_markup=record_set_time_kb(schedule, data["date"], data["machine"])
    )


@laundry_router.callback_query(F.data == "broken")
async def broken_machine(call: CallbackQuery):
    await call.answer("Эта машинка на тех.обслуживании. Запись недоступна.", show_alert=True)


@laundry_router.callback_query(F.data.contains("set_time"))
async def set_time(call: CallbackQuery, state: FSMContext):
    _, begin_time, end_time = call.data.split()
    data = await state.get_data()
    data["all_laundries"].append((data["machine"], begin_time, end_time))
    await state.update_data(all_laundries=data["all_laundries"])
    await cart_view(call.message, state)


@laundry_router.callback_query(F.data == "manual_time")
async def receive_manual_time(call: CallbackQuery, state: FSMContext):
    await state.set_state(RecordInfo.manual_time)
    await call.message.edit_caption(
        caption="Введите ваше время в формате чч:мм-чч:мм (например, 09:00-10:00)",
        reply_markup=get_cancel_kb()
    )


@laundry_router.callback_query(F.data == "laundry_my")
async def laundry_my(call: CallbackQuery, state: FSMContext):
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    bookings = schedule.get_user_bookings(str(call.message.chat.id))
    if not bookings:
        await call.message.edit_caption(caption="У вас нет записей.", reply_markup=get_start_kb())
        return
    text_lines = ["Ваши записи:"]
    kb = InlineKeyboardBuilder()
    for i, (date, machine, b, e, label) in enumerate(bookings, 1):
        text_lines.append(f"{i}. {date} • Машинка {machine} • {b}-{e}")
        kb.add(InlineKeyboardButton(text=f"Отменить {i}", callback_data=f"laundry_cancel {date} {machine} {b} {e}"))
    kb.add(InlineKeyboardButton(text="Назад", callback_data="start_from_button"))
    kb.adjust(1)
    await call.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())


@laundry_router.callback_query(F.data.contains("laundry_cancel"))
async def laundry_cancel(call: CallbackQuery):
    _, date, machine, b, e = call.data.split()
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    ok = schedule.remove_booking(date, machine, b, e, str(call.message.chat.id))
    if not ok:
        await call.message.edit_caption(caption="Не удалось отменить запись (возможно, она уже удалена).", reply_markup=get_start_kb())
        return
    try:
        refund_amount = _amount_for_record(machine, b, e)
    except ValueError:
        refund_amount = 0
    if refund_amount > 0:
        credit_balance(call.message.chat.id, refund_amount, "laundry_cancel")
    bookings = schedule.get_user_bookings(str(call.message.chat.id))
    if not bookings:
        msg = "Запись отменена. У вас больше нет записей."
        if refund_amount > 0:
            msg += f"\nВозврат: {refund_amount} ₽"
        await call.message.edit_caption(caption=msg, reply_markup=get_start_kb())
        return
    text_lines = ["Запись отменена. Ваши актуальные записи:"]
    if refund_amount > 0:
        text_lines.append(f"Возврат: {refund_amount} ₽")
    kb = InlineKeyboardBuilder()
    for i, (d, m, bb, ee, label) in enumerate(bookings, 1):
        text_lines.append(f"{i}. {d} • Машинка {m} • {bb}-{ee}")
        kb.add(InlineKeyboardButton(text=f"Отменить {i}", callback_data=f"laundry_cancel {d} {m} {bb} {ee}"))
    kb.add(InlineKeyboardButton(text="Назад", callback_data="start_from_button"))
    kb.adjust(1)
    await call.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())


@laundry_router.message(RecordInfo.manual_time)
async def send_manual_time(message: Message, state: FSMContext):
    try:
        begin_time, end_time = message.text.split("-")
        datetime.strptime(begin_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
        schedule = Schedule(SCHEDULE_PATH)
        schedule.load_schedule()
        data = await state.get_data()
        if schedule.is_time_available(data["date"], data["machine"], begin_time, end_time):
            data["all_laundries"].append((data["machine"], begin_time, end_time))
            data = await state.update_data(all_laundries=data["all_laundries"])
            await cart_view(data["original_message"], state)
            return
        await data["original_message"].edit_caption(
            caption="На это время нельзя записаться!!! Введите другое время",
            reply_markup=record_set_time_kb(schedule, data["date"], data["machine"])
        )
    except Exception as e:
        print(e)
        await state.set_state(RecordInfo.manual_time)
        await data["original_message"].edit_caption(
            caption="Неверный формат ввода!!! Попробуйте ещё раз",
            reply_markup=record_set_time_kb(schedule, data["date"], data["machine"])
        )


async def cart_view(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_text = "Итого:\n"
    for record in data["all_laundries"]:
        msg_text += f"- Машинка {record[0]}: {record[1]}-{record[2]}\n"
    amount_rub, total_hours = _calc_total_amount(data["all_laundries"])
    msg_text += f"\nСтоимость: {amount_rub} ₽ ({total_hours:.2f} ч.)"
    await message.edit_caption(caption=msg_text, reply_markup=cart_kb(data["date"]))


@laundry_router.callback_query(F.data == "laundry_pay")
async def laundry_pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    records = data.get("all_laundries") or []
    if not records:
        await call.answer("Нет выбранных бронирований для оплаты.", show_alert=True)
        return

    amount_rub, total_hours = _calc_total_amount(records)
    balance = get_balance(call.message.chat.id)
    if balance < amount_rub:
        await call.message.edit_media(
            InputMediaPhoto(
                media=FSInputFile("falt.jpg"),
                caption=f"Недостаточно средств.\nК оплате: {amount_rub} ₽\nБаланс: {balance} ₽",
            ),
            reply_markup=get_insufficient_funds_kb(),
        )
        return

    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()
    for machine_id, begin_time, end_time in records:
        if not schedule.is_time_available(data["date"], str(machine_id), begin_time, end_time):
            await call.message.edit_caption(
                caption=f"Время {begin_time}-{end_time} на машинку {machine_id} уже занято. Выбери другое.",
                reply_markup=record_set_time_kb(schedule, data["date"], machine_id),
            )
            return

    if not debit_balance(call.message.chat.id, amount_rub, "laundry_booking"):
        await call.message.edit_media(
            InputMediaPhoto(
                media=FSInputFile("falt.jpg"),
                caption="Недостаточно средств для оплаты.",
            ),
            reply_markup=get_insufficient_funds_kb(),
        )
        return

    user = is_registered(call.message.chat.id)
    label = f"{user.surname} {user.name[0]}." if user else "Пользователь"
    for machine_id, begin_time, end_time in records:
        schedule.add_booking(data["date"], machine_id, begin_time, end_time, label, str(call.message.chat.id))

    new_balance = get_balance(call.message.chat.id)
    await state.clear()
    await call.message.edit_media(
        InputMediaPhoto(
            media=FSInputFile("falt.jpg"),
            caption=f"Бронь подтверждена.\nСписано: {amount_rub} ₽\nБаланс: {new_balance} ₽",
        ),
        reply_markup=get_start_kb(),
    )