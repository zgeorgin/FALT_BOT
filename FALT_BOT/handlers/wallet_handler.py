from aiogram import Router, F
from aiogram.enums.content_type import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile, InputMediaPhoto

from config import YOOKASSA_RETURN_URL
from keyboards.payment_keyboards import get_payment_kb
from keyboards.wallet_keyboards import get_wallet_menu_kb, get_wallet_topup_back_kb
from services.wallet.wallet import create_topup, get_balance, check_topup


wallet_router = Router()


class WalletStates(StatesGroup):
    topup_amount = State()


@wallet_router.callback_query(F.data == "wallet")
async def wallet_menu(call: CallbackQuery):
    balance = get_balance(call.message.chat.id)
    await call.message.edit_caption(
        caption=f"Баланс: {balance} ₽",
        reply_markup=get_wallet_menu_kb(),
    )


@wallet_router.callback_query(F.data == "wallet_topup")
async def wallet_topup(call: CallbackQuery, state: FSMContext):
    await state.set_state(WalletStates.topup_amount)
    await call.message.edit_caption(
        caption="Введите сумму пополнения в рублях (целое число):",
        reply_markup=get_wallet_topup_back_kb(),
    )


@wallet_router.message(WalletStates.topup_amount)
async def wallet_topup_amount(message: Message, state: FSMContext):
    if message.content_type != ContentType.TEXT:
        await message.answer("Неверный формат. Отправьте число.", reply_markup=get_wallet_topup_back_kb())
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно целое число рублей.", reply_markup=get_wallet_topup_back_kb())
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.", reply_markup=get_wallet_topup_back_kb())
        return
    if not YOOKASSA_RETURN_URL:
        await message.answer("Оплата временно недоступна. Нет return_url.", reply_markup=get_wallet_topup_back_kb())
        return

    try:
        payment = await create_topup(message.chat.id, amount)
    except Exception:
        await message.answer("Не удалось создать платеж. Попробуйте позже.", reply_markup=get_wallet_topup_back_kb())
        return

    await state.clear()
    await message.answer_photo(
        photo=FSInputFile("falt.jpg"),
        caption=f"К оплате: {amount} ₽\nПосле оплаты нажмите «Проверить оплату».",
        reply_markup=get_payment_kb(payment.confirmation_url, payment.payment_id),
    )


@wallet_router.callback_query(F.data.startswith("payment_check "))
async def wallet_payment_check(call: CallbackQuery):
    payment_id = call.data.split(maxsplit=1)[1]
    result = await check_topup(payment_id, expected_user_id=call.message.chat.id)

    if result.status == "not_found":
        await call.answer("Платеж не найден.", show_alert=True)
        return
    if result.status == "not_owner":
        await call.answer("Этот платеж не принадлежит вам.", show_alert=True)
        return
    if result.status == "unsupported":
        await call.answer("Неверный тип платежа.", show_alert=True)
        return
    if result.status == "error":
        await call.answer("Не удалось проверить платеж. Попробуйте позже.", show_alert=True)
        return
    if result.status in ("succeeded", "already_succeeded"):
        balance = result.balance if result.balance is not None else get_balance(call.message.chat.id)
        await call.message.edit_media(
            InputMediaPhoto(media=FSInputFile("falt.jpg"), caption=f"Оплата подтверждена ✅\nБаланс: {balance} ₽"),
            reply_markup=get_wallet_menu_kb(),
        )
        return
    if result.status == "canceled":
        await call.message.edit_media(
            InputMediaPhoto(media=FSInputFile("falt.jpg"), caption="Оплата отменена."),
            reply_markup=get_wallet_menu_kb(),
        )
        return

    await call.answer("Оплата еще не завершена. Попробуйте позже.", show_alert=True)
