"""Форматирование дат и сводок для сообщений."""
from datetime import date, datetime

from config import CONSOLES, TIMEZONE
from services.pricing import tariff_label

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def fmt_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d:%d.%m}"


def fmt_dt(dt: datetime) -> str:
    local = dt.astimezone(TIMEZONE)
    return f"{WEEKDAYS[local.weekday()]}, {local:%d.%m.%Y %H:%M}"


def booking_summary(console: str, full_name: str, phone: str, tariff_type: str,
                    duration: int, start: datetime, end: datetime, price: int) -> str:
    return (
        f"🎮 Консоль: <b>{CONSOLES[console].title}</b>\n"
        f"👤 ФИО: <b>{full_name}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n"
        f"⏱ Тариф: <b>{tariff_label(tariff_type, duration)}</b>\n"
        f"📦 Выдача: <b>{fmt_dt(start)}</b>\n"
        f"🔙 Возврат: <b>{fmt_dt(end)}</b>\n"
        f"💰 Стоимость: <b>{price} ₽</b>"
    )
