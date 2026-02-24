from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, MenuButtonWebApp,
)
from database.db import is_registered
from config import ADMIN_CHAT_ID, MINI_APP_URL

mini_app_router = Router()


def _mini_app_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🧺 Открыть Mini App",
            web_app=WebAppInfo(url=MINI_APP_URL),
        )],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="laundry_my")],
        [InlineKeyboardButton(text="💰 Кошелёк", callback_data="wallet")],
    ])


@mini_app_router.message(Command("miniapp"))
async def cmd_miniapp(message: Message):
    if not MINI_APP_URL:
        await message.answer("Mini App пока недоступен. Обратитесь к администратору.")
        return

    user = is_registered(message.from_user.id)
    if not user:
        await message.answer(
            "Сначала зарегистрируйтесь через /start",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Зарегистрироваться", callback_data="registration")]
            ]),
        )
        return

    if not user.email:
        await message.answer(
            "Для Mini App нужен email. Используйте /setemail",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📧 Указать email", callback_data="set_email_prompt")]
            ]),
        )
        return

    await message.answer(
        f"Привет, {user.name}! Откройте Mini App:",
        reply_markup=_mini_app_kb(),
    )


@mini_app_router.message(Command("bookings"))
async def cmd_bookings(message: Message):
    """Быстрый доступ к записям через команду"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.answer(
        "Ваши записи:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Посмотреть записи", callback_data="laundry_my")]
        ]),
    )


async def set_mini_app_menu(bot: Bot):
    """Устанавливает кнопку меню Mini App глобально"""
    if not MINI_APP_URL:
        return
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🧺 FALT App",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        )
    except Exception as e:
        import logging
        logging.warning(f"Could not set menu button: {e}")


# ── Уведомления из Mini App ──────────────────────────────────────────────

async def notify_booking_created(bot: Bot, user_id: int, booking: dict):
    try:
        await bot.send_message(
            user_id,
            f"✅ Бронирование создано через Mini App!\n"
            f"📅 {booking['date']}  🧺 Машинка {booking['machine_id']}\n"
            f"🕐 {booking['start_time']}–{booking['end_time']}\n"
            f"Статус: ожидает оплаты",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Мои записи", callback_data="laundry_my")]
            ]),
        )
    except Exception:
        pass


async def notify_payment_success(bot: Bot, user_id: int, amount: int, new_balance: int):
    try:
        await bot.send_message(
            user_id,
            f"💰 Оплата прошла!\nСписано: {amount} ₽\nБаланс: {new_balance} ₽",
        )
    except Exception:
        pass
