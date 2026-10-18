from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from config import DAILY, HOURLY, WEEKLY
from services.schedule import (
    available_dates,
    available_starts,
    calc_end,
    day_slots,
    is_free,
    is_valid_start,
    max_concurrent,
)

TZ = ZoneInfo("Europe/Moscow")
DAY = date(2026, 10, 7)
NEXT = DAY + timedelta(days=1)
# «Сейчас» — вечер накануне, чтобы весь DAY был в будущем
NOW = datetime(2026, 10, 6, 20, 0, tzinfo=TZ)


def at(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


# ---------- границы рабочего дня ----------

def test_day_slots_from_0830_to_1730_step_30():
    slots = day_slots(DAY, TZ)
    assert slots[0] == at(DAY, 8, 30)
    assert slots[-1] == at(DAY, 17, 30)
    assert len(slots) == 19
    assert all(b - a == timedelta(minutes=30) for a, b in zip(slots, slots[1:]))


def test_past_slots_hidden_today():
    now = at(DAY, 12, 10)
    starts = available_starts(DAY, HOURLY, 1, [], 1, now, TZ)
    assert starts[0] == at(DAY, 12, 30)
    assert at(DAY, 12, 0) not in starts


def test_slot_equal_to_now_is_hidden():
    starts = available_starts(DAY, HOURLY, 1, [], 1, at(DAY, 9, 0), TZ)
    assert starts[0] == at(DAY, 9, 30)


def test_no_slots_after_close():
    assert available_starts(DAY, HOURLY, 1, [], 1, at(DAY, 17, 45), TZ) == []


def test_is_valid_start_rejects_off_grid_and_out_of_hours():
    assert is_valid_start(at(DAY, 8, 30), NOW, TZ)
    assert not is_valid_start(at(DAY, 8, 0), NOW, TZ)
    assert not is_valid_start(at(DAY, 9, 15), NOW, TZ)
    assert not is_valid_start(at(DAY, 18, 0), NOW, TZ)


def test_booking_window_is_14_days():
    today = NOW.date()
    assert is_valid_start(at(today + timedelta(days=13), 10), NOW, TZ)
    assert not is_valid_start(at(today + timedelta(days=14), 10), NOW, TZ)
    dates = available_dates(HOURLY, 1, [], 1, NOW, TZ)
    # сегодня в 20:00 слотов нет, остаются 13 следующих дней
    assert dates[0] == today + timedelta(days=1)
    assert dates[-1] == today + timedelta(days=13)
    assert len(dates) == 13


# ---------- время возврата ----------

def test_hourly_end_same_day():
    assert calc_end(at(DAY, 10), HOURLY, 3, TZ) == at(DAY, 13)


def test_hourly_end_exactly_at_close_stays_same_day():
    assert calc_end(at(DAY, 17), HOURLY, 1, TZ) == at(DAY, 18)
    assert calc_end(at(DAY, 8, 30), HOURLY, 9, TZ) == at(DAY, 17, 30)


@pytest.mark.parametrize("start_h, start_m, hours", [
    (17, 30, 1),   # 18:30 → перенос
    (8, 30, 10),   # 18:30 → перенос
    (8, 30, 12),   # 20:30 → перенос
    (17, 30, 12),  # 05:30 следующего дня → всё равно 8:30
])
def test_hourly_end_after_close_moves_to_next_morning(start_h, start_m, hours):
    assert calc_end(at(DAY, start_h, start_m), HOURLY, hours, TZ) == at(NEXT, 8, 30)


@pytest.mark.parametrize("tariff, days", [(DAILY, 1), (DAILY, 2), (WEEKLY, 7)])
def test_daily_and_weekly_return_same_time(tariff, days):
    start = at(DAY, 14, 30)
    assert calc_end(start, tariff, days, TZ) == start + timedelta(days=days)


def test_invalid_tariff_rejected():
    with pytest.raises(ValueError):
        calc_end(at(DAY, 10), HOURLY, 13, TZ)
    with pytest.raises(ValueError):
        calc_end(at(DAY, 10), DAILY, 3, TZ)


# ---------- пересечения броней ----------

def test_touching_intervals_do_not_overlap():
    busy = [(at(DAY, 10), at(DAY, 12))]
    assert is_free(at(DAY, 12), at(DAY, 13), busy, 1)
    assert is_free(at(DAY, 9), at(DAY, 10), busy, 1)


def test_overlap_blocks_single_unit():
    busy = [(at(DAY, 10), at(DAY, 12))]
    assert not is_free(at(DAY, 11), at(DAY, 13), busy, 1)
    assert not is_free(at(DAY, 9), at(DAY, 10, 30), busy, 1)
    assert not is_free(at(DAY, 9), at(DAY, 14), busy, 1)  # охватывает целиком


def test_slots_around_existing_booking():
    busy = [(at(DAY, 10), at(DAY, 12))]
    starts = available_starts(DAY, HOURLY, 1, busy, 1, NOW, TZ)
    assert at(DAY, 9) in starts           # 9:00–10:00 ок
    assert at(DAY, 9, 30) not in starts   # 9:30–10:30 пересекается
    assert at(DAY, 11, 30) not in starts
    assert at(DAY, 12) in starts


def test_overnight_hourly_booking_blocks_next_morning():
    # 17:30 на 1 час → устройство занято до 8:30 следующего дня
    busy = [(at(DAY, 17, 30), calc_end(at(DAY, 17, 30), HOURLY, 1, TZ))]
    assert at(DAY, 17, 30) not in available_starts(DAY, HOURLY, 1, busy, 1, NOW, TZ)
    assert available_starts(NEXT, HOURLY, 1, busy, 1, NOW, TZ)[0] == at(NEXT, 8, 30)
    # а вечером того же дня суточная аренда, пересекающая ночь, невозможна
    assert at(DAY, 16) not in available_starts(DAY, DAILY, 1, busy, 1, NOW, TZ)


def test_daily_booking_blocks_following_day_until_same_time():
    busy = [(at(DAY, 12), at(NEXT, 12))]
    starts = available_starts(NEXT, HOURLY, 1, busy, 1, NOW, TZ)
    assert starts[0] == at(NEXT, 12)


def test_date_hidden_when_fully_booked():
    week = [(at(DAY, 8, 30), at(DAY + timedelta(days=7), 8, 30))]
    dates = available_dates(HOURLY, 1, week, 1, NOW, TZ)
    for i in range(7):
        assert DAY + timedelta(days=i) not in dates
    assert DAY + timedelta(days=7) in dates


def test_long_tariff_hides_dates_with_conflicts_later():
    # Бронь через 3 дня: неделю нельзя начать ни в один из ближайших 3 дней
    busy = [(at(DAY + timedelta(days=3), 10), at(DAY + timedelta(days=3), 11))]
    dates = available_dates(WEEKLY, 7, busy, 1, NOW, TZ)
    assert DAY not in dates
    # а вот в сам день брони после её окончания — можно
    assert DAY + timedelta(days=3) in dates


# ---------- лимит по количеству устройств ----------

def test_two_units_allow_one_parallel_booking():
    busy = [(at(DAY, 10), at(DAY, 12))]
    assert is_free(at(DAY, 11), at(DAY, 13), busy, 2)
    busy.append((at(DAY, 11), at(DAY, 13)))
    assert not is_free(at(DAY, 11, 30), at(DAY, 12, 30), busy, 2)


def test_non_simultaneous_bookings_dont_add_up():
    # Две брони пересекают интервал, но не друг друга → в каждый момент занята 1 единица
    busy = [(at(DAY, 9), at(DAY, 11)), (at(DAY, 12), at(DAY, 14))]
    assert max_concurrent(at(DAY, 10), at(DAY, 13), busy) == 1
    assert is_free(at(DAY, 10), at(DAY, 13), busy, 2)
    assert not is_free(at(DAY, 10), at(DAY, 13), busy, 1)


def test_back_to_back_bookings_count_as_one():
    busy = [(at(DAY, 9), at(DAY, 11)), (at(DAY, 11), at(DAY, 13))]
    assert max_concurrent(at(DAY, 8, 30), at(DAY, 14), busy) == 1


def test_zero_units_never_free():
    assert available_dates(HOURLY, 1, [], 0, NOW, TZ) == []
