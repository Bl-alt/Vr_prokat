"""Фабрики callback_data для inline-кнопок."""
from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="menu"):
    action: str  # home | book | features | terms | cancel


class ConsoleCb(CallbackData, prefix="console"):
    code: str


class TariffCb(CallbackData, prefix="tariff"):
    type: str


class DurationCb(CallbackData, prefix="dur"):
    value: int


class DateCb(CallbackData, prefix="date"):
    day: str  # YYYYMMDD


class TimeCb(CallbackData, prefix="time"):
    hm: str  # HHMM


class BackCb(CallbackData, prefix="back"):
    to: str  # tariff | date


class ConfirmCb(CallbackData, prefix="confirm"):
    ok: bool


class CancelPickCb(CallbackData, prefix="cpick"):
    booking_id: int


class CancelConfirmCb(CallbackData, prefix="cconf"):
    booking_id: int
    ok: bool
