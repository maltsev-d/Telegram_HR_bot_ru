from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_data)
        ]
    ])


def single_button_keyboard(text: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback_data)]
    ])

def decision_keyboard(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принят", callback_data=f"decision_accept_{user_id}")
    kb.button(text="❌ Непринят", callback_data=f"decision_reject_{user_id}")
    return kb.as_markup()