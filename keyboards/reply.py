"""Reply-клавиатуры (нужны только для кнопки «Поделиться контактом»)."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from keyboards.inline import HOME_TEXT

SHARE_CONTACT_TEXT = "📱 Поделиться контактом"


def phone_request() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHARE_CONTACT_TEXT, request_contact=True)],
            [KeyboardButton(text=HOME_TEXT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="+7 900 000-00-00",
    )
