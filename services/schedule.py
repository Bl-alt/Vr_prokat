"""Логика расписания: время возврата, свободные слоты, доступные даты.

Все функции чистые (не ходят в БД и не смотрят на часы сами) — текущий момент
и список занятых интервалов передаются параметрами, поэтому их легко тестировать.
Все datetime — aware (с часовым поясом).
"""
from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import (
    BOOKING_DAYS_AHEAD,
    HOURLY,
    SLOT_STEP_MINUTES,
    TIMEZONE,
    WORK_END,
    WORK_START,
)
from services.pricing import validate_tariff

Interval = tuple[datetime, datetime]


def _at(day: date, t: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, t, tzinfo=tz)


def calc_end(start: datetime, tariff_type: str, duration: int, tz: ZoneInfo = TIMEZONE) -> datetime:
    """Момент возврата устройства (до него устройство считается занятым).

    Почасовая аренда: если она заканчивается позже закрытия (18:00), возврат
    переносится на следующий день к открытию (8:30).
    Сутки/неделя: возврат в то же время через N суток.
    """
    validate_tariff(tariff_type, duration)
    local = start.astimezone(tz)
    if tariff_type == HOURLY:
        end = local + timedelta(hours=duration)
        if end > _at(local.date(), WORK_END, tz):
            end = _at(local.date() + timedelta(days=1), WORK_START, tz)
        return end
    # Арифметика aware-datetime с ZoneInfo идёт по «настенному» времени,
    # поэтому возврат будет в то же локальное время.
    return local + timedelta(days=duration)


def day_slots(day: date, tz: ZoneInfo = TIMEZONE) -> list[datetime]:
    """Все возможные времена выдачи в день: 8:30, 9:00, …, 17:30."""
    slots = []
    current = _at(day, WORK_START, tz)
    close = _at(day, WORK_END, tz)
    while current < close:
        slots.append(current)
        current += timedelta(minutes=SLOT_STEP_MINUTES)
    return slots


def max_concurrent(start: datetime, end: datetime, busy: Iterable[Interval]) -> int:
    """Максимальное число броней, одновременно пересекающихся с [start, end)."""
    events: list[tuple[datetime, int]] = []
    for b_start, b_end in busy:
        if b_start < end and start < b_end:  # интервалы полуоткрытые
            events.append((max(b_start, start), 1))
            events.append((min(b_end, end), -1))
    # При равном времени сначала закрываем (-1), потом открываем (+1):
    # бронь, закончившаяся в 10:00, не мешает брони, начинающейся в 10:00.
    events.sort(key=lambda e: (e[0], e[1]))
    current = peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def is_free(start: datetime, end: datetime, busy: Iterable[Interval], units: int) -> bool:
    """Хватает ли устройств на весь интервал [start, end)."""
    return max_concurrent(start, end, busy) < units


def is_valid_start(start: datetime, now: datetime, tz: ZoneInfo = TIMEZONE,
                   days_ahead: int = BOOKING_DAYS_AHEAD) -> bool:
    """Время выдачи попадает в сетку слотов, в окно записи и ещё не прошло."""
    local = start.astimezone(tz)
    today = now.astimezone(tz).date()
    if not today <= local.date() < today + timedelta(days=days_ahead):
        return False
    return local in day_slots(local.date(), tz) and local > now


def available_starts(day: date, tariff_type: str, duration: int, busy: Sequence[Interval],
                     units: int, now: datetime, tz: ZoneInfo = TIMEZONE,
                     days_ahead: int = BOOKING_DAYS_AHEAD) -> list[datetime]:
    """Свободные времена выдачи в указанный день для заданной длительности."""
    return [
        s for s in day_slots(day, tz)
        if is_valid_start(s, now, tz, days_ahead)
        and is_free(s, calc_end(s, tariff_type, duration, tz), busy, units)
    ]


def available_dates(tariff_type: str, duration: int, busy: Sequence[Interval], units: int,
                    now: datetime, tz: ZoneInfo = TIMEZONE,
                    days_ahead: int = BOOKING_DAYS_AHEAD) -> list[date]:
    """Даты в окне записи, где есть хотя бы один свободный слот."""
    today = now.astimezone(tz).date()
    days = (today + timedelta(days=i) for i in range(days_ahead))
    return [
        d for d in days
        if available_starts(d, tariff_type, duration, busy, units, now, tz, days_ahead)
    ]
