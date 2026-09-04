from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_payment_kb(confirmation_url: str, payment_id: str) -> InlineKeyboardMarkup:
    inline_kb_list = [
        [InlineKeyboardButton(text="Оплатить", url=confirmation_url)],
        [InlineKeyboardButton(text="Проверить оплату", callback_data=f"payment_check {payment_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
