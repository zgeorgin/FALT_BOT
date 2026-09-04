from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.enums.content_type import ContentType
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
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
import tempfile
import asyncio
import time

# === 💳 Robokassa imports ===
import hashlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


laundry_router = Router()

SCHEDULE_PATH = os.getenv("LAUNDRY_DATA_PATH")


# Рекомендуется хранить в переменных окружения
# ROBOKASSA_MERCHANT_LOGIN, ROBOKASSA_PASSWORD1, ROBOKASSA_PASSWORD2,
# ROBOKASSA_IS_TEST, ROBOKASSA_HASH_ALGORITHM
# ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN")
# ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1")
# ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2")
# ROBOKASSA_IS_TEST = os.getenv("ROBOKASSA_IS_TEST", "0") == "1"
# ROBOKASSA_HASH_ALGORITHM = os.getenv("ROBOKASSA_HASH_ALGORITHM", "md5").lower()

ROBOKASSA_MERCHANT_LOGIN = os.getenv("Monterada")
ROBOKASSA_PASSWORD1 = os.getenv("K3gUf2jS9f2pUzMMBRR4")
ROBOKASSA_PASSWORD2 = os.getenv("XNT3nu25JHNZJXDSt08D")
ROBOKASSA_IS_TEST = 0
ROBOKASSA_HASH_ALGORITHM = "md5"


ROBOKASSA_PAYMENT_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
ROBOKASSA_OPSTATE_URL = (
    "https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt"
)


def _robokassa_hash(value: str) -> str:
    """Считает подпись алгоритмом, выбранным в настройках магазина Robokassa."""
    algorithms = {
        "md5": hashlib.md5,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }
    hash_func = algorithms.get(ROBOKASSA_HASH_ALGORITHM)
    if hash_func is None:
        raise ValueError(
            "ROBOKASSA_HASH_ALGORITHM должен быть md5, sha256 или sha512"
        )
    return hash_func(value.encode("utf-8")).hexdigest()


def _build_robokassa_payment_url(
    inv_id: int,
    out_sum: str,
    description: str,
    expiration_date: str,
) -> str:
    """Формирует URL платежной страницы Robokassa."""
    signature = _robokassa_hash(
        f"{ROBOKASSA_MERCHANT_LOGIN}:{out_sum}:{inv_id}:{ROBOKASSA_PASSWORD1}"
    )

    params = {
        "MerchantLogin": ROBOKASSA_MERCHANT_LOGIN,
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": description,
        "SignatureValue": signature,
        "Culture": "ru",
        "Encoding": "utf-8",
        "ExpirationDate": expiration_date,
    }

    if ROBOKASSA_IS_TEST:
        params["IsTest"] = "1"

    return f"{ROBOKASSA_PAYMENT_URL}?{urllib.parse.urlencode(params)}"


def _get_robokassa_payment_state(inv_id: int) -> int | None:
    """
    Получает состояние операции через OpStateExt.

    Важно: Robokassa не поддерживает OpStateExt для тестовых платежей.
    """
    if ROBOKASSA_IS_TEST:
        return None

    signature = _robokassa_hash(
        f"{ROBOKASSA_MERCHANT_LOGIN}:{inv_id}:{ROBOKASSA_PASSWORD2}"
    )

    params = urllib.parse.urlencode(
        {
            "MerchantLogin": ROBOKASSA_MERCHANT_LOGIN,
            "InvoiceID": str(inv_id),
            "Signature": signature,
        }
    )

    try:
        with urllib.request.urlopen(
            f"{ROBOKASSA_OPSTATE_URL}?{params}",
            timeout=10,
        ) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {"r": "http://merchant.roboxchange.com/WebService/"}

        result_code = root.findtext("r:Result/r:Code", namespaces=ns)
        if result_code != "0":
            return None

        state_code = root.findtext("r:State/r:Code", namespaces=ns)
        return int(state_code) if state_code is not None else None
    except Exception as exc:
        print(f"Robokassa OpStateExt error: {exc}")
        return None


def _pending_label(payment_id: str, expires_ts: int, user_label: str) -> str:
    # label сохраняется в расписании, чтобы отличать «холд» от финальной брони
    return f"PENDING|{payment_id}|{expires_ts}|{user_label}"


def _final_label(user_label: str) -> str:
    return user_label

async def _watch_payment_and_finalize(
    bot,
    chat_id: int,
    message_id: int,
    payment_id: int,
    date: str,
    records: list[tuple[str, str, str]],
    expires_ts: int,
):
    """Автоматически проверяет оплату до дедлайна.
    - State.Code == 100 -> переводит PENDING в финальную бронь
    - таймаут -> снимает холд
    Работает пока бот запущен.
    """
    schedule = Schedule(SCHEDULE_PATH)
    poll_interval = 5  # секунд

    # Проверяем до дедлайна
    while int(time.time()) < int(expires_ts):
        status = await asyncio.to_thread(
            _get_robokassa_payment_state,
            payment_id,
        )

        if status == 100:
            schedule.load_schedule()
            user = is_registered(chat_id)

            # Переводим PENDING -> финальная бронь
            for machine_id, time_from, time_to in records:
                schedule.remove_booking(date, str(machine_id), time_from, time_to, str(chat_id))
                schedule.add_booking(
                    date,
                    machine_id,
                    time_from,
                    time_to,
                    _final_label(f"{user.surname} {user.name[0]}"),
                    str(chat_id),
                )

            # Обновим то же сообщение
            try:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption="Оплата подтверждена ✅\nБронь стиральных машин подтверждена и сохранена.",
                    reply_markup=get_start_kb(),
                )
            except Exception:
                await bot.send_message(
                    chat_id,
                    "Оплата подтверждена ✅\nБронь стиральных машин подтверждена и сохранена.",
                    reply_markup=get_start_kb(),
                )
            return

        await asyncio.sleep(poll_interval)

    # Таймаут -> снимаем холд, если Robokassa не подтвердила оплату
    status = await asyncio.to_thread(
        _get_robokassa_payment_state,
        payment_id,
    )

    if status == 100:
        # на границе времени могло успеть пройти
        return await _watch_payment_and_finalize(bot, chat_id, message_id, payment_id, date, records, int(time.time()) + 1)

    schedule.load_schedule()
    removed_any = False
    for machine_id, time_from, time_to in records:
        ok = schedule.remove_booking(date, str(machine_id), time_from, time_to, str(chat_id))
        removed_any = removed_any or bool(ok)

    if removed_any:
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption="⏳ Время на оплату истекло (10 минут).\nБронь отменена. Если нужно — выбери время снова.",
                reply_markup=get_start_kb(),
            )
        except Exception:
            await bot.send_message(
                chat_id,
                "⏳ Время на оплату истекло (10 минут). Бронь отменена. Если нужно — выбери время снова.",
                reply_markup=get_start_kb(),
            )

async def _cancel_hold_after_10m(bot, chat_id: int, payment_id: int, date: str, records: list[tuple[str, str, str]], expires_ts: int):
    """Через 10 минут после создания платежа отменяем бронь, если платеж не успешен."""
    now = int(time.time())
    delay = max(0, expires_ts - now)
    await asyncio.sleep(delay)

    status = await asyncio.to_thread(
        _get_robokassa_payment_state,
        payment_id,
    )
    if status == 100:
        return

    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()

    removed_any = False
    for machine_id, time_from, time_to in records:
        ok = schedule.remove_booking(date, str(machine_id), time_from, time_to, str(chat_id))
        removed_any = removed_any or bool(ok)

    if removed_any:
        try:
            await bot.send_message(
                chat_id,
                "⏳ Время на оплату истекло (10 минут). Бронь отменена. Если нужно — выбери время снова.",
            )
        except Exception:
            pass

class RecordInfo(StatesGroup):
    date = State()
    machine = State()
    manual_time = State()
    exit_state = State()
    all_laundries = State()
    original_message = State()
    filepath = State()
    payment_id = State()
    hold_expires_ts = State()
    hold_records = State()

@laundry_router.callback_query(lambda callback : callback.data in ["laundry_record","exit_from_record"])
async def start_record(call : CallbackQuery, state : FSMContext):
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Выберите день: "), reply_markup=record_set_day_kb(datetime.today()))
    await state.update_data(all_laundries = [])
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
    await call.message.edit_media(InputMediaPhoto(media=FSInputFile(filepath), caption="Выберите машинку: "), reply_markup=record_set_machine_kb())
    await state.update_data(date=date)
    await state.update_data(filepath=filepath)
    await state.update_data(original_message=call.message)
    await state.set_state(RecordInfo.machine)

@laundry_router.callback_query(F.data.contains("Машинка"))
async def set_machine(call: CallbackQuery, state: FSMContext):
    machine = call.data.split()[1]
    if machine in ["4"]:
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
    bookings = schedule.get_user_bookings(str(call.message.chat.id))
    if not bookings:
        await call.message.edit_caption(caption="Запись отменена. У вас больше нет записей.", reply_markup=get_start_kb())
        return
    text_lines = ["Запись отменена. Ваши актуальные записи:"]
    kb = InlineKeyboardBuilder()
    for i, (d, m, bb, ee, label) in enumerate(bookings, 1):
        text_lines.append(f"{i}. {d} • Машинка {m} • {bb}-{ee}")
        kb.add(InlineKeyboardButton(text=f"Отменить {i}", callback_data=f"laundry_cancel {d} {m} {bb} {ee}"))
    kb.add(InlineKeyboardButton(text="Назад", callback_data="start_from_button"))
    kb.adjust(1)
    await call.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())


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
async def laundry_pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    PRICE_PER_HOUR_WASH = 50
    PRICE_PER_HOUR_DRY = 20

    if not data.get("all_laundries"):
        await call.message.edit_caption("Корзина пуста.", reply_markup=get_start_kb())
        return

    # Проверяем, что настроены реквизиты Robokassa
    if not (
        ROBOKASSA_MERCHANT_LOGIN
        and ROBOKASSA_PASSWORD1
        and ROBOKASSA_PASSWORD2
    ):
        await call.message.edit_caption(
            "Оплата сейчас недоступна: не настроены данные Robokassa.",
            reply_markup=get_start_kb(),
        )
        return

    user = is_registered(call.message.chat.id)
    schedule = Schedule(SCHEDULE_PATH)
    schedule.load_schedule()

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    price = 0
    for machine_id, time_from, time_to in data["all_laundries"]:
        start = to_minutes(time_from)
        end = to_minutes(time_to)
        if end <= start:
            await call.message.edit_caption(
                f"Некорректный интервал: {time_from}-{time_to}",
                reply_markup=get_start_kb(),
            )
            return
        current_minutes = end - start
        price += current_minutes / 60 * PRICE_PER_HOUR_WASH if int(machine_id) < 6 else current_minutes / 60 * PRICE_PER_HOUR_DRY

    # Защита от ситуации “пока платили — время заняли” (перед созданием платежа)
    for machine_id, time_from, time_to in data["all_laundries"]:
        if not schedule.is_time_available(data["date"], str(machine_id), time_from, time_to):
            await call.message.edit_caption(
                f"Время {time_from}-{time_to} на машинку {machine_id} уже занято. Выбери другое.",
                reply_markup=record_set_time_kb(schedule, data["date"], machine_id),
            )
            return

    # === 1) Формируем ссылку на оплату Robokassa ===
    # InvId должен быть уникальным в рамках магазина.
    inv_id = int(f"{int(time.time())}{random.randint(100, 999)}")
    out_sum = f"{price:.2f}"
    description = (
        f"Стирка {data['date']}, "
        f"{len(data['all_laundries'])} слот(ов)"
    )

    expiration_dt = datetime.fromtimestamp(time.time() + 10 * 60)
    expiration_date = expiration_dt.strftime("%Y-%m-%dT%H:%M")

    confirmation_url = _build_robokassa_payment_url(
        inv_id=inv_id,
        out_sum=out_sum,
        description=description,
        expiration_date=expiration_date,
    )

    # === 2) Ставим ХОЛД выбранных слотов на 10 минут ===
    hold_expires_ts = int(time.time()) + 10 * 60

    for machine_id, time_from, time_to in data["all_laundries"]:
        schedule.add_booking(
            data["date"],
            machine_id,
            time_from,
            time_to,
            _pending_label(
                str(inv_id),
                hold_expires_ts,
                f"{user.surname} {user.name[0]}",
            ),
            str(call.message.chat.id),
        )

    await state.update_data(
        payment_id=inv_id,
        hold_expires_ts=hold_expires_ts,
        hold_records=data["all_laundries"],
    )
    await state.set_state(RecordInfo.payment_id)

    asyncio.create_task(
        _watch_payment_and_finalize(
            call.bot,
            call.message.chat.id,
            call.message.message_id,
            inv_id,
            data["date"],
            data["all_laundries"],
            hold_expires_ts,
        )
    )


    # Кнопки: перейти к оплате + проверить оплату
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Оплатить", url=confirmation_url))
    kb.add(InlineKeyboardButton(text="Отмена", callback_data="start_from_button"))
    kb.adjust(1)

    await call.message.edit_media(
        InputMediaPhoto(
            media=FSInputFile("falt.jpg"),
            caption=(
                f"К оплате: {price:.2f} ₽\n\n"
                "Мы забронировали выбранные слоты на 10 минут.\n"
                "1) Нажми «Оплатить» и заверши оплату на сайте.\n"
                "Если не оплатить за 10 минут — бронь автоматически отменится."
            ),
        ),
        reply_markup=kb.as_markup(),
    )

