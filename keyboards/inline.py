"""Inline-клавиатуры."""
from collections.abc import Sequence
from datetime import date, datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CONSOLES, DAILY, DAILY_DURATIONS, HOURLY, HOURLY_DURATIONS, TIMEZONE, WEEKLY
from db.database import Booking
from keyboards.callbacks import (
    BackCb,
    CancelConfirmCb,
    CancelPickCb,
    ConfirmCb,
    ConsoleCb,
    DateCb,
    DurationCb,
    MenuCb,
    TariffCb,
    TimeCb,
)
from services.formatting import fmt_date
from services.pricing import tariff_label

HOME_TEXT = "🏠 В главное меню"


def home_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text=HOME_TEXT, callback_data=MenuCb(action="home").pack())


def main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 Запись", callback_data=MenuCb(action="book"))
    b.button(text="🎮 Возможности и игры", callback_data=MenuCb(action="features"))
    b.button(text="📋 Условия проката", callback_data=MenuCb(action="terms"))
    b.button(text="❌ Отменить запись", callback_data=MenuCb(action="cancel"))
    b.adjust(1)
    return b.as_markup()


def home_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[home_button()]])


def consoles() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in CONSOLES.values():
        b.button(text=c.title, callback_data=ConsoleCb(code=c.code))
    b.adjust(1)
    b.row(home_button())
    return b.as_markup()


def tariffs() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="1–12 часов", callback_data=TariffCb(type=HOURLY))
    b.button(text="1–2 дня", callback_data=TariffCb(type=DAILY))
    b.button(text="Неделя", callback_data=TariffCb(type=WEEKLY))
    b.adjust(1)
    b.row(home_button())
    return b.as_markup()


def durations(tariff_type: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    values = HOURLY_DURATIONS if tariff_type == HOURLY else DAILY_DURATIONS
    for v in values:
        b.button(text=tariff_label(tariff_type, v), callback_data=DurationCb(value=v))
    b.adjust(4 if tariff_type == HOURLY else 2)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=BackCb(to="tariff").pack()))
    b.row(home_button())
    return b.as_markup()


def dates(days: Sequence[date]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(text=fmt_date(d), callback_data=DateCb(day=f"{d:%Y%m%d}"))
    b.adjust(3)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=BackCb(to="tariff").pack()))
    b.row(home_button())
    return b.as_markup()


def times(slots: Sequence[datetime]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        local = s.astimezone(TIMEZONE)
        b.button(text=f"{local:%H:%M}", callback_data=TimeCb(hm=f"{local:%H%M}"))
    b.adjust(4)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=BackCb(to="date").pack()))
    b.row(home_button())
    return b.as_markup()


def confirm() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Согласен", callback_data=ConfirmCb(ok=True))
    b.button(text="↩️ Отмена", callback_data=ConfirmCb(ok=False))
    b.adjust(2)
    b.row(home_button())
    return b.as_markup()


def user_bookings(bookings: Sequence[Booking]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        local = bk.start_at.astimezone(TIMEZONE)
        title = CONSOLES[bk.console].title.replace("Oculus ", "")
        b.button(
            text=f"{title} · {fmt_date(local.date())} {local:%H:%M} · {tariff_label(bk.tariff_type, bk.duration)}",
            callback_data=CancelPickCb(booking_id=bk.id),
        )
    b.adjust(1)
    b.row(home_button())
    return b.as_markup()


def cancel_confirm(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Да, отменить", callback_data=CancelConfirmCb(booking_id=booking_id, ok=True))
    b.button(text="Нет", callback_data=CancelConfirmCb(booking_id=booking_id, ok=False))
    b.adjust(2)
    return b.as_markup()
