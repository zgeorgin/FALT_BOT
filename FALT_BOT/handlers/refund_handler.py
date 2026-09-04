import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User as TgUser

from config import ADMIN_CHAT_ID
from database.db import (
    add_refund_log,
    create_refund_request,
    get_refund_request,
    is_registered,
    resolve_refund_request,
)
from keyboards.keyboards import get_start_kb
from keyboards.refund_keyboards import (
    get_refund_admin_kb,
    get_refund_cancel_kb,
    get_refund_confirm_kb,
)
from services.wallet.wallet import credit_balance


refund_router = Router()

refund_logger = logging.getLogger("refunds")
if not refund_logger.handlers:
    file_handler = logging.FileHandler("logs/refunds.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    refund_logger.addHandler(file_handler)
refund_logger.setLevel(logging.INFO)


class RefundUserFlow(StatesGroup):
    problem = State()
    amount = State()
    confirm = State()


class RefundAdminFlow(StatesGroup):
    decline_comment = State()
    change_amount = State()


def parse_amount(raw_amount: str) -> int:
    value = float(raw_amount.strip().replace(",", "."))
    if value <= 0:
        raise ValueError("Amount must be positive")
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        raise ValueError("Amount must be integer")
    return int(rounded)


def format_amount(amount: int) -> str:
    return f"{int(amount)} ₽"


def user_label(user: TgUser | None) -> str:
    if user is None:
        return "unknown"
    if user.username:
        return f"@{user.username}"
    full_name = (user.full_name or "").strip()
    if full_name:
        return full_name
    return str(user.id)


def build_admin_refund_text(request_id: int, user_display: str, problem_text: str, requested_amount: int) -> str:
    return (
        "Новый запрос на возврат средств\n\n"
        f"ID заявки: {request_id}\n"
        f"Пользователь: {user_display}\n"
        f"Сумма к возврату: {format_amount(requested_amount)}\n"
        f"Описание проблемы: {problem_text}"
    )


async def edit_message_content(message: Message, text: str, reply_markup=None):
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await message.edit_text(text=text, reply_markup=reply_markup)


async def edit_tracked_message(state: FSMContext, bot, text: str, reply_markup=None):
    data = await state.get_data()
    chat_id = data.get("dialog_chat_id")
    message_id = data.get("dialog_message_id")
    is_photo = data.get("dialog_is_photo", False)
    if chat_id is None or message_id is None:
        return
    if is_photo:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            reply_markup=reply_markup,
        )
    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )


@refund_router.callback_query(F.data == "refund_start")
async def refund_start(call: CallbackQuery, state: FSMContext):
    if not is_registered(call.message.chat.id):
        await call.answer("Сначала нужно зарегистрироваться", show_alert=True)
        return

    await state.clear()
    await state.update_data(
        dialog_chat_id=call.message.chat.id,
        dialog_message_id=call.message.message_id,
        dialog_is_photo=bool(call.message.photo),
    )
    await state.set_state(RefundUserFlow.problem)
    await edit_message_content(
        call.message,
        "Опишите проблему со стиркой одним сообщением:",
        get_refund_cancel_kb(),
    )


@refund_router.callback_query(F.data == "refund_cancel")
async def refund_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_message_content(
        call.message,
        "Запрос на возврат отменен.",
        get_start_kb(),
    )


@refund_router.message(RefundUserFlow.problem)
async def refund_problem_received(message: Message, state: FSMContext):
    if not message.text:
        await edit_tracked_message(
            state,
            message.bot,
            "Нужен текст с описанием проблемы.",
            get_refund_cancel_kb(),
        )
        return

    await state.update_data(problem_text=message.text.strip())
    await state.set_state(RefundUserFlow.amount)
    await edit_tracked_message(
        state,
        message.bot,
        "Укажите сумму возврата в рублях (целое число, например: 150).",
        get_refund_cancel_kb(),
    )


@refund_router.message(RefundUserFlow.amount)
async def refund_amount_received(message: Message, state: FSMContext):
    if not message.text:
        await edit_tracked_message(
            state,
            message.bot,
            "Введите сумму текстом, например: 150",
            get_refund_cancel_kb(),
        )
        return

    try:
        requested_amount = parse_amount(message.text)
    except ValueError:
        await edit_tracked_message(
            state,
            message.bot,
            "Неверный формат суммы. Нужны целые рубли, пример: 150",
            get_refund_cancel_kb(),
        )
        return

    data = await state.update_data(requested_amount=requested_amount)
    await state.set_state(RefundUserFlow.confirm)
    await edit_tracked_message(
        state,
        message.bot,
        "Проверьте заявку:\n\n"
        f"Проблема: {data['problem_text']}\n"
        f"Сумма: {format_amount(requested_amount)}\n\n"
        "Отправить запрос?",
        get_refund_confirm_kb(),
    )


@refund_router.callback_query(F.data == "refund_submit", RefundUserFlow.confirm)
async def refund_submit(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = int(call.from_user.id)
    problem_text = data["problem_text"]
    requested_amount = int(data["requested_amount"])

    request_id = create_refund_request(
        user_id=user_id,
        problem_text=problem_text,
        requested_amount=requested_amount,
    )
    add_refund_log(
        request_id=request_id,
        action="request_created",
        actor_id=user_id,
        comment=problem_text,
        amount=requested_amount,
    )

    await call.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=build_admin_refund_text(
            request_id=request_id,
            user_display=user_label(call.from_user),
            problem_text=problem_text,
            requested_amount=requested_amount,
        ),
        reply_markup=get_refund_admin_kb(request_id),
    )

    refund_logger.info(
        "refund_created request_id=%s user_id=%s requested_amount=%s",
        request_id,
        user_id,
        requested_amount,
    )

    await state.clear()
    await edit_message_content(
        call.message,
        f"Запрос №{request_id} отправлен администраторам.",
        get_start_kb(),
    )


@refund_router.callback_query(F.data.startswith("refund_approve "))
async def refund_approve(call: CallbackQuery):
    request_id = int(call.data.split()[1])
    refund_request = get_refund_request(request_id)
    if refund_request is None:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    if refund_request.status != "new":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    is_updated = resolve_refund_request(
        request_id=request_id,
        status="approved",
        admin_id=call.from_user.id,
        approved_amount=int(refund_request.requested_amount),
    )
    if not is_updated:
        await call.answer("Заявка уже обработана другим администратором", show_alert=True)
        return

    new_balance = credit_balance(
        int(refund_request.user_id),
        int(refund_request.requested_amount),
        "refund_approved",
        f"refund:{request_id}",
    )

    add_refund_log(
        request_id=request_id,
        action="approved",
        actor_id=call.from_user.id,
        amount=int(refund_request.requested_amount),
    )
    refund_logger.info(
        "refund_approved request_id=%s admin_id=%s amount=%s",
        request_id,
        call.from_user.id,
        int(refund_request.requested_amount),
    )

    admin_display = user_label(call.from_user)
    await call.message.edit_text(
        text=(
            f"Заявка #{request_id}\n"
            "Статус: APPROVED\n"
            f"Сумма возврата: {format_amount(int(refund_request.requested_amount))}\n"
            f"Администратор: {admin_display}"
        ),
        reply_markup=None,
    )
    await call.bot.send_message(
        chat_id=refund_request.user_id,
        text=(
            f"Заявка на возврат №{request_id} одобрена.\n"
            f"Сумма к возврату: {format_amount(int(refund_request.requested_amount))}\n"
            f"Новый баланс: {format_amount(int(new_balance or 0))}\n"
        ),
        reply_markup=None,
    )


@refund_router.callback_query(F.data.startswith("refund_decline "))
async def refund_decline_start(call: CallbackQuery, state: FSMContext):
    request_id = int(call.data.split()[1])
    refund_request = get_refund_request(request_id)
    if refund_request is None:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    if refund_request.status != "new":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    await state.set_state(RefundAdminFlow.decline_comment)
    await state.update_data(
        admin_chat_id=call.message.chat.id,
        admin_message_id=call.message.message_id,
        admin_is_photo=bool(call.message.photo),
        request_id=request_id,
    )
    await edit_message_content(
        call.message,
        f"Введите комментарий для отклонения заявки #{request_id}:",
        None,
    )


@refund_router.message(RefundAdminFlow.decline_comment)
async def refund_decline_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    request_id = int(data["request_id"])
    comment = (message.text or "").strip()
    if not comment:
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text=f"Комментарий не может быть пустым.\nВведите комментарий для отклонения заявки #{request_id}:",
            reply_markup=None,
        )
        return

    refund_request = get_refund_request(request_id)
    if refund_request is None:
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка не найдена.",
            reply_markup=None,
        )
        return
    if refund_request.status != "new":
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка уже обработана другим администратором.",
            reply_markup=None,
        )
        return

    is_updated = resolve_refund_request(
        request_id=request_id,
        status="declined",
        admin_id=message.from_user.id,
        admin_comment=comment,
    )
    if not is_updated:
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка уже обработана другим администратором.",
            reply_markup=None,
        )
        return

    add_refund_log(
        request_id=request_id,
        action="declined",
        actor_id=message.from_user.id,
        comment=comment,
    )
    refund_logger.info(
        "refund_declined request_id=%s admin_id=%s comment=%s",
        request_id,
        message.from_user.id,
        comment,
    )

    admin_display = user_label(message.from_user)
    await message.bot.edit_message_text(
        chat_id=data["admin_chat_id"],
        message_id=data["admin_message_id"],
        text=(
            f"Заявка #{request_id}\n"
            "Статус: DECLINED\n"
            f"Комментарий: {comment}\n"
            f"Администратор: {admin_display}"
        ),
        reply_markup=None,
    )
    await message.bot.send_message(
        chat_id=refund_request.user_id,
        text=(
            f"Заявка на возврат №{request_id} отклонена.\n"
            f"Комментарий администратора: {comment}\n"
        ),
        reply_markup=None,
    )
    await state.clear()


@refund_router.callback_query(F.data.startswith("refund_change "))
async def refund_change_start(call: CallbackQuery, state: FSMContext):
    request_id = int(call.data.split()[1])
    refund_request = get_refund_request(request_id)
    if refund_request is None:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    if refund_request.status != "new":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    await state.set_state(RefundAdminFlow.change_amount)
    await state.update_data(
        admin_chat_id=call.message.chat.id,
        admin_message_id=call.message.message_id,
        admin_is_photo=bool(call.message.photo),
        request_id=request_id,
    )
    await edit_message_content(
        call.message,
        f"Введите новую сумму возврата для заявки #{request_id}:",
        None,
    )


@refund_router.message(RefundAdminFlow.change_amount)
async def refund_change_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    request_id = int(data["request_id"])

    try:
        approved_amount = parse_amount(message.text or "")
    except ValueError:
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text=f"Неверный формат суммы.\nВведите новую сумму возврата для заявки #{request_id}:",
            reply_markup=None,
        )
        return

    refund_request = get_refund_request(request_id)
    if refund_request is None:
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка не найдена.",
            reply_markup=None,
        )
        return
    if refund_request.status != "new":
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка уже обработана другим администратором.",
            reply_markup=None,
        )
        return

    is_updated = resolve_refund_request(
        request_id=request_id,
        status="changed_amount_approved",
        admin_id=message.from_user.id,
        approved_amount=approved_amount,
        admin_comment="Сумма изменена администратором",
    )
    if not is_updated:
        await state.clear()
        await message.bot.edit_message_text(
            chat_id=data["admin_chat_id"],
            message_id=data["admin_message_id"],
            text="Заявка уже обработана другим администратором.",
            reply_markup=None,
        )
        return

    new_balance = credit_balance(
        int(refund_request.user_id),
        int(approved_amount),
        "refund_changed_amount",
        f"refund:{request_id}",
    )

    add_refund_log(
        request_id=request_id,
        action="changed_amount_approved",
        actor_id=message.from_user.id,
        amount=approved_amount,
        comment="Сумма изменена администратором",
    )
    refund_logger.info(
        "refund_changed_amount request_id=%s admin_id=%s amount=%s",
        request_id,
        message.from_user.id,
        approved_amount,
    )

    admin_display = user_label(message.from_user)
    await message.bot.edit_message_text(
        chat_id=data["admin_chat_id"],
        message_id=data["admin_message_id"],
        text=(
            f"Заявка #{request_id}\n"
            "Статус: CHANGED_AMOUNT_APPROVED\n"
            f"Новая сумма возврата: {format_amount(approved_amount)}\n"
            f"Администратор: {admin_display}"
        ),
        reply_markup=None,
    )
    await message.bot.send_message(
        chat_id=refund_request.user_id,
        text=(
            f"Заявка на возврат №{request_id} одобрена с измененной суммой.\n"
            f"Итоговая сумма: {format_amount(approved_amount)}\n"
            f"Новый баланс: {format_amount(int(new_balance or 0))}\n"
            f"Обработал: {admin_display}"
        ),
        reply_markup=None,
    )
    await state.clear()
