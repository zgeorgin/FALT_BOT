from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_wallet_menu_kb() -> InlineKeyboardMarkup:
    inline_kb_list = [
        [InlineKeyboardButton(text="Пополнить", callback_data="wallet_topup")],
        [InlineKeyboardButton(text="Назад", callback_data="start_from_button")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def get_wallet_topup_back_kb() -> InlineKeyboardMarkup:
    inline_kb_list = [
        [InlineKeyboardButton(text="Назад", callback_data="wallet")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def get_insufficient_funds_kb() -> InlineKeyboardMarkup:
    inline_kb_list = [
        [InlineKeyboardButton(text="Пополнить кошелек", callback_data="wallet_topup")],
        [InlineKeyboardButton(text="Назад", callback_data="start_from_button")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
