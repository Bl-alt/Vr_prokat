"""Хранилище броней на SQLite (aiosqlite).

Время хранится в ISO 8601 в UTC со смещением (`2026-10-07T05:30:00+00:00`):
значение несёт часовой пояс, а строки корректно сравниваются в SQL.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

from services.schedule import Interval, is_free

ACTIVE = "active"
CANCELLED = "cancelled"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    full_name   TEXT    NOT NULL,
    phone       TEXT    NOT NULL,
    console     TEXT    NOT NULL,
    tariff_type TEXT    NOT NULL,
    duration    INTEGER NOT NULL,
    start_at    TEXT    NOT NULL,
    end_at      TEXT    NOT NULL,
    price       INTEGER NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bookings_console_time ON bookings (console, status, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id, status, start_at);
"""


def _to_db(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("Ожидается datetime с часовым поясом")
    return dt.astimezone(timezone.utc).isoformat()


def _from_db(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass
class Booking:
    id: int
    user_id: int
    full_name: str
    phone: str
    console: str
    tariff_type: str
    duration: int
    start_at: datetime
    end_at: datetime
    price: int
    status: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Booking":
        data = dict(row)
        for key in ("start_at", "end_at", "created_at"):
            data[key] = _from_db(data[key])
        return cls(**data)


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None
        # Соединение одно на всех; транзакции разных апдейтов не должны перемешиваться
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        # isolation_level=None — транзакциями управляем сами (BEGIN IMMEDIATE ниже)
        self._conn = await aiosqlite.connect(self.path, isolation_level=None)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена")
        return self._conn

    async def busy_intervals(self, console: str, after: datetime) -> list[Interval]:
        """Активные брони консоли, которые заканчиваются позже `after`."""
        async with self.conn.execute(
            "SELECT start_at, end_at FROM bookings "
            "WHERE console = ? AND status = ? AND end_at > ?",
            (console, ACTIVE, _to_db(after)),
        ) as cur:
            rows = await cur.fetchall()
        return [(_from_db(r["start_at"]), _from_db(r["end_at"])) for r in rows]

    async def create_booking_if_free(self, *, user_id: int, full_name: str, phone: str,
                                     console: str, tariff_type: str, duration: int,
                                     start_at: datetime, end_at: datetime, price: int,
                                     units: int, now: datetime) -> int | None:
        """Атомарно перепроверяет доступность и сохраняет бронь.

        Возвращает id брони или None, если слот уже занят.
        BEGIN IMMEDIATE берёт блокировку на запись, поэтому две параллельные
        попытки забронировать последний слот не пройдут обе.
        """
        async with self._write_lock:
            return await self._create_locked(
                user_id=user_id, full_name=full_name, phone=phone, console=console,
                tariff_type=tariff_type, duration=duration, start_at=start_at,
                end_at=end_at, price=price, units=units, now=now,
            )

    async def _create_locked(self, *, user_id, full_name, phone, console, tariff_type,
                             duration, start_at, end_at, price, units, now) -> int | None:
        conn = self.conn
        await conn.execute("BEGIN IMMEDIATE")
        try:
            async with conn.execute(
                "SELECT start_at, end_at FROM bookings "
                "WHERE console = ? AND status = ? AND start_at < ? AND end_at > ?",
                (console, ACTIVE, _to_db(end_at), _to_db(start_at)),
            ) as cur:
                busy = [(_from_db(r["start_at"]), _from_db(r["end_at"])) for r in await cur.fetchall()]
            if not is_free(start_at, end_at, busy, units):
                await conn.execute("ROLLBACK")
                return None
            cur = await conn.execute(
                "INSERT INTO bookings (user_id, full_name, phone, console, tariff_type, duration, "
                "start_at, end_at, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, full_name, phone, console, tariff_type, duration,
                 _to_db(start_at), _to_db(end_at), price, ACTIVE, _to_db(now)),
            )
            booking_id = cur.lastrowid
            await conn.execute("COMMIT")
            return booking_id
        except BaseException:
            await conn.execute("ROLLBACK")
            raise

    async def get_booking(self, booking_id: int) -> Booking | None:
        async with self.conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)) as cur:
            row = await cur.fetchone()
        return Booking.from_row(row) if row else None

    async def user_future_bookings(self, user_id: int, now: datetime) -> list[Booking]:
        async with self.conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND status = ? AND start_at > ? "
            "ORDER BY start_at",
            (user_id, ACTIVE, _to_db(now)),
        ) as cur:
            rows = await cur.fetchall()
        return [Booking.from_row(r) for r in rows]

    async def cancel_booking(self, booking_id: int, user_id: int, now: datetime) -> Booking | None:
        """Помечает будущую активную бронь пользователя отменённой. None — если отменять нечего."""
        async with self._write_lock:
            cur = await self.conn.execute(
                "UPDATE bookings SET status = ? "
                "WHERE id = ? AND user_id = ? AND status = ? AND start_at > ?",
                (CANCELLED, booking_id, user_id, ACTIVE, _to_db(now)),
            )
        if cur.rowcount == 0:
            return None
        return await self.get_booking(booking_id)
