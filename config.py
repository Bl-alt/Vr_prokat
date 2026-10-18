"""Настройки бота и бизнес-параметры проката."""
import os
from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


# --- Окружение (.env) ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
_admin_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
if _admin_raw and not _admin_raw.lstrip("-").isdigit():
    raise SystemExit(
        f"ADMIN_CHAT_ID должен быть числом (например 123456789), а не {_admin_raw!r}. "
        "Свой id можно узнать у @userinfobot."
    )
ADMIN_CHAT_ID: int | None = int(_admin_raw) if _admin_raw else None
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow")
DB_PATH: str = os.getenv("DB_PATH", "bookings.db").strip() or "bookings.db"

# --- Режим работы ---
WORK_START = time(8, 30)   # первая выдача / возврат
WORK_END = time(18, 0)     # закрытие пункта проката
SLOT_STEP_MINUTES = 30     # шаг времени начала аренды
BOOKING_DAYS_AHEAD = 14    # на сколько дней вперёд можно записаться (включая сегодня)


# --- Консоли ---
@dataclass(frozen=True)
class Console:
    code: str
    title: str


CONSOLES: dict[str, Console] = {
    "quest2": Console("quest2", "Oculus Quest 2"),
    "quest3": Console("quest3", "Oculus Quest 3"),
}

# Сколько единиц каждой модели есть в наличии
CONSOLE_UNITS: dict[str, int] = {
    "quest2": _int_env("QUEST2_UNITS", 1),
    "quest3": _int_env("QUEST3_UNITS", 1),
}

# --- Тарифы ---
HOURLY = "hourly"
DAILY = "daily"
WEEKLY = "weekly"

HOUR_PRICE = 500
DAY_PRICE = 2500
WEEK_PRICE = 7000
WEEK_DAYS = 7

HOURLY_DURATIONS = list(range(1, 13))  # 1…12 часов
DAILY_DURATIONS = [1, 2]               # 1 или 2 суток
