import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from config import HOURLY
from db.database import CANCELLED, Database

TZ = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 10, 6, 20, 0, tzinfo=TZ)
START = datetime(2026, 10, 7, 10, 0, tzinfo=TZ)


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


def _booking(user_id=1, start=START, hours=2, units=1):
    return dict(user_id=user_id, full_name="Иван Петров", phone="+79123456789", console="quest3",
                tariff_type=HOURLY, duration=hours, start_at=start,
                end_at=start + timedelta(hours=hours), price=500 * hours, units=units, now=NOW)


async def test_create_and_read_keeps_timezone(db):
    bid = await db.create_booking_if_free(**_booking())
    b = await db.get_booking(bid)
    assert b.start_at == START and b.start_at.tzinfo is not None
    assert await db.busy_intervals("quest3", NOW) == [(START, START + timedelta(hours=2))]
    assert await db.busy_intervals("quest2", NOW) == []


async def test_overlap_rejected_and_unit_limit(db):
    assert await db.create_booking_if_free(**_booking())
    assert await db.create_booking_if_free(**_booking(start=START + timedelta(hours=1))) is None
    # при двух единицах вторая пересекающаяся бронь проходит, третья — нет
    assert await db.create_booking_if_free(**_booking(start=START + timedelta(hours=1), units=2))
    assert await db.create_booking_if_free(**_booking(start=START + timedelta(minutes=90), units=2)) is None


async def test_race_only_one_wins(db):
    results = await asyncio.gather(*(db.create_booking_if_free(**_booking(user_id=i)) for i in range(5)))
    assert sum(r is not None for r in results) == 1


async def test_cancel_marks_status_and_frees_slot(db):
    bid = await db.create_booking_if_free(**_booking())
    assert await db.cancel_booking(bid, user_id=2, now=NOW) is None  # чужая бронь
    cancelled = await db.cancel_booking(bid, user_id=1, now=NOW)
    assert cancelled.status == CANCELLED
    assert await db.get_booking(bid) is not None  # не удалена
    assert await db.user_future_bookings(1, NOW) == []
    assert await db.create_booking_if_free(**_booking(user_id=3))


async def test_past_bookings_not_listed(db):
    await db.create_booking_if_free(**_booking())
    assert len(await db.user_future_bookings(1, NOW)) == 1
    assert await db.user_future_bookings(1, START) == []
    assert await db.cancel_booking(1, 1, now=START + timedelta(minutes=1)) is None
