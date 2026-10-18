"""Расчёт стоимости аренды."""
from config import (
    DAILY,
    DAILY_DURATIONS,
    DAY_PRICE,
    HOUR_PRICE,
    HOURLY,
    HOURLY_DURATIONS,
    WEEK_DAYS,
    WEEK_PRICE,
    WEEKLY,
)


def validate_tariff(tariff_type: str, duration: int) -> None:
    """Бросает ValueError, если такой комбинации тарифа и длительности нет."""
    if tariff_type == HOURLY and duration in HOURLY_DURATIONS:
        return
    if tariff_type == DAILY and duration in DAILY_DURATIONS:
        return
    if tariff_type == WEEKLY and duration == WEEK_DAYS:
        return
    raise ValueError(f"Недопустимый тариф: {tariff_type}/{duration}")


def calc_price(tariff_type: str, duration: int) -> int:
    """Стоимость в рублях. duration — часы для почасового тарифа, сутки для остальных."""
    validate_tariff(tariff_type, duration)
    if tariff_type == HOURLY:
        return HOUR_PRICE * duration
    if tariff_type == DAILY:
        return DAY_PRICE * duration
    return WEEK_PRICE


def tariff_label(tariff_type: str, duration: int) -> str:
    """Человекочитаемое название тарифа: «3 часа», «2 суток», «Неделя (7 суток)»."""
    if tariff_type == HOURLY:
        return f"{duration} {plural(duration, 'час', 'часа', 'часов')}"
    if tariff_type == DAILY:
        return f"{duration} {plural(duration, 'сутки', 'суток', 'суток')}"
    return f"Неделя ({WEEK_DAYS} суток)"


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many
