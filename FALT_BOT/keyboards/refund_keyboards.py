from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_refund_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="refund_cancel")]]
    )


def get_refund_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отправить запрос", callback_data="refund_submit")],
            [InlineKeyboardButton(text="Отмена", callback_data="refund_cancel")],
        ]
    )


def get_refund_admin_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оформить возврат", callback_data=f"refund_approve {request_id}")],
            [InlineKeyboardButton(text="Отклонить и оставить комментарий", callback_data=f"refund_decline {request_id}")],
            [InlineKeyboardButton(text="Изменить сумму возврата", callback_data=f"refund_change {request_id}")],
        ]
    )
