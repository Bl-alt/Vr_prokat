"""Сценарий записи (FSM)."""
from datetime import date, datetime, time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import content
from config import CONSOLE_UNITS, CONSOLES, DAILY, HOURLY, TIMEZONE, WEEK_DAYS, WEEKLY
from db.database import Database
from handlers.states import BookingStates
from handlers.utils import edit_or_send, notify_admin, now
from keyboards import inline as kb
from keyboards import reply as rkb
from keyboards.callbacks import (
    BackCb,
    ConfirmCb,
    ConsoleCb,
    DateCb,
    DurationCb,
    MenuCb,
    TariffCb,
    TimeCb,
)
from services import schedule
from services.formatting import booking_summary, fmt_date
from services.pricing import calc_price, tariff_label, validate_tariff
from services.validators import normalize_full_name, normalize_phone

router = Router(name="booking")

TARIFF_PROMPT = "Выберите тип аренды:"


# ---------- вспомогательное ----------

def _parse_day(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        return None


def _parse_time(raw: str) -> time | None:
    try:
        return datetime.strptime(raw, "%H%M").time()
    except ValueError:
        return None


def _header(data: dict) -> str:
    return (f"🎮 {CONSOLES[data['console']].title} · "
            f"{tariff_label(data['tariff_type'], data['duration'])}\n\n")


async def _show_tariffs(callback: CallbackQuery, state: FSMContext, prefix: str = "") -> None:
    await state.set_state(BookingStates.tariff)
    await edit_or_send(callback, prefix + TARIFF_PROMPT, kb.tariffs())


async def _show_dates(callback: CallbackQuery, state: FSMContext, db: Database,
                      prefix: str = "") -> None:
    data = await state.get_data()
    console, tariff_type, duration = data["console"], data["tariff_type"], data["duration"]
    current = now()
    busy = await db.busy_intervals(console, current)
    days = schedule.available_dates(tariff_type, duration, busy, CONSOLE_UNITS[console], current)
    if not days:
        await _show_tariffs(
            callback, state,
            prefix + _header(data) + "😔 На ближайшие дни свободного времени для такой аренды нет. "
            "Попробуйте другой тариф.\n\n",
        )
        return
    await state.set_state(BookingStates.date)
    await edit_or_send(callback, prefix + _header(data) + "📅 Выберите дату выдачи:", kb.dates(days))


async def _show_times(callback: CallbackQuery, state: FSMContext, db: Database, day: date,
                      prefix: str = "") -> bool:
    """Показывает свободное время на дату. False — если слотов уже нет."""
    data = await state.get_data()
    console = data["console"]
    current = now()
    busy = await db.busy_intervals(console, current)
    slots = schedule.available_starts(day, data["tariff_type"], data["duration"], busy,
                                      CONSOLE_UNITS[console], current)
    if not slots:
        return False
    await state.update_data(day=f"{day:%Y%m%d}")
    await state.set_state(BookingStates.time)
    await edit_or_send(callback, prefix + _header(data) + f"📅 {fmt_date(day)}\n🕒 Выберите время выдачи:",
                       kb.times(slots))
    return True


# ---------- шаг 1: консоль ----------

@router.callback_query(MenuCb.filter(F.action == "book"))
async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BookingStates.console)
    await edit_or_send(callback, "Выберите консоль:", kb.consoles())
    await callback.answer()


@router.callback_query(BookingStates.console, ConsoleCb.filter())
async def pick_console(callback: CallbackQuery, callback_data: ConsoleCb, state: FSMContext) -> None:
    if callback_data.code not in CONSOLES:
        await callback.answer("Неизвестная консоль", show_alert=True)
        return
    await state.update_data(console=callback_data.code)
    await state.set_state(BookingStates.name)
    await edit_or_send(
        callback,
        f"🎮 {CONSOLES[callback_data.code].title}\n\n"
        "Введите <b>имя и фамилию</b> (например: Иван Петров):",
        kb.home_only(),
    )
    await callback.answer()


# ---------- шаг 2: имя ----------

@router.message(BookingStates.name, F.text)
async def enter_name(message: Message, state: FSMContext) -> None:
    full_name = normalize_full_name(message.text)
    if full_name is None:
        await message.answer(
            "⚠️ Не получилось распознать имя. Введите имя и фамилию — минимум два слова, "
            "только буквы. Например: <i>Иван Петров</i>",
            reply_markup=kb.home_only(),
        )
        return
    await state.update_data(full_name=full_name)
    await state.set_state(BookingStates.phone)
    await message.answer(
        f"Приятно познакомиться, {full_name.split()[0]}!\n\n"
        "📞 Отправьте номер телефона текстом (например, +7 912 345-67-89) "
        f"или нажмите «{rkb.SHARE_CONTACT_TEXT}» внизу.",
        reply_markup=rkb.phone_request(),
    )


@router.message(BookingStates.name)
async def enter_name_invalid(message: Message) -> None:
    await message.answer("⚠️ Пожалуйста, отправьте имя и фамилию текстом.", reply_markup=kb.home_only())


# ---------- шаг 3: телефон ----------

async def _accept_phone(message: Message, state: FSMContext, raw: str) -> None:
    phone = normalize_phone(raw)
    if phone is None:
        await message.answer(
            "⚠️ Номер не похож на российский мобильный. Введите его в формате "
            "+7 9XX XXX-XX-XX или 8 9XX XXX-XX-XX.",
            reply_markup=rkb.phone_request(),
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.tariff)
    await message.answer(f"✅ Телефон: {phone}", reply_markup=ReplyKeyboardRemove())
    await message.answer(TARIFF_PROMPT, reply_markup=kb.tariffs())


@router.message(BookingStates.phone, F.contact)
async def enter_phone_contact(message: Message, state: FSMContext) -> None:
    await _accept_phone(message, state, message.contact.phone_number)


@router.message(BookingStates.phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext) -> None:
    await _accept_phone(message, state, message.text)


@router.message(BookingStates.phone)
async def enter_phone_invalid(message: Message) -> None:
    await message.answer("⚠️ Отправьте номер текстом или кнопкой «Поделиться контактом».",
                         reply_markup=rkb.phone_request())


# ---------- шаг 4: тариф и длительность ----------

@router.callback_query(BookingStates.tariff, TariffCb.filter())
async def pick_tariff(callback: CallbackQuery, callback_data: TariffCb, state: FSMContext,
                      db: Database) -> None:
    tariff_type = callback_data.type
    if tariff_type == WEEKLY:
        await state.update_data(tariff_type=WEEKLY, duration=WEEK_DAYS)
        await _show_dates(callback, state, db)
    elif tariff_type in (HOURLY, DAILY):
        await state.update_data(tariff_type=tariff_type)
        await state.set_state(BookingStates.duration)
        question = "Сколько часов?" if tariff_type == HOURLY else "На сколько суток?"
        await edit_or_send(callback, question, kb.durations(tariff_type))
    else:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return
    await callback.answer()


@router.callback_query(BookingStates.duration, DurationCb.filter())
async def pick_duration(callback: CallbackQuery, callback_data: DurationCb, state: FSMContext,
                        db: Database) -> None:
    data = await state.get_data()
    try:
        validate_tariff(data["tariff_type"], callback_data.value)
    except ValueError:
        await callback.answer("Недопустимая длительность", show_alert=True)
        return
    await state.update_data(duration=callback_data.value)
    await _show_dates(callback, state, db)
    await callback.answer()


# ---------- шаги 5–6: дата и время ----------

@router.callback_query(BookingStates.date, DateCb.filter())
async def pick_date(callback: CallbackQuery, callback_data: DateCb, state: FSMContext,
                    db: Database) -> None:
    day = _parse_day(callback_data.day)
    if day is None or not await _show_times(callback, state, db, day):
        await callback.answer("На эту дату свободного времени уже нет 😔", show_alert=True)
        await _show_dates(callback, state, db)
        return
    await callback.answer()


@router.callback_query(BookingStates.time, TimeCb.filter())
async def pick_time(callback: CallbackQuery, callback_data: TimeCb, state: FSMContext,
                    db: Database) -> None:
    data = await state.get_data()
    day, t = _parse_day(data.get("day", "")), _parse_time(callback_data.hm)
    if day is None or t is None:
        await callback.answer("Некорректное время", show_alert=True)
        await _show_dates(callback, state, db)
        return

    console, tariff_type, duration = data["console"], data["tariff_type"], data["duration"]
    start = datetime.combine(day, t, tzinfo=TIMEZONE)
    end = schedule.calc_end(start, tariff_type, duration)
    current = now()
    busy = await db.busy_intervals(console, current)
    if not (schedule.is_valid_start(start, current)
            and schedule.is_free(start, end, busy, CONSOLE_UNITS[console])):
        await callback.answer("Это время уже недоступно, выберите другое", show_alert=True)
        if not await _show_times(callback, state, db, day):
            await _show_dates(callback, state, db)
        return

    await state.update_data(start=start.isoformat())
    await state.set_state(BookingStates.confirm)
    summary = booking_summary(console, data["full_name"], data["phone"], tariff_type, duration,
                              start, end, calc_price(tariff_type, duration))
    await edit_or_send(callback, "📝 <b>Проверьте данные записи</b>\n\n" + summary, kb.confirm())
    await callback.answer()


@router.callback_query(BookingStates.duration, BackCb.filter(F.to == "tariff"))
@router.callback_query(BookingStates.date, BackCb.filter(F.to == "tariff"))
async def back_to_tariff(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_tariffs(callback, state)
    await callback.answer()


@router.callback_query(BookingStates.time, BackCb.filter(F.to == "date"))
async def back_to_date(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await _show_dates(callback, state, db)
    await callback.answer()


# ---------- шаг 7: подтверждение ----------

@router.callback_query(BookingStates.confirm, ConfirmCb.filter(F.ok == False))  # noqa: E712
async def confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    # Консоль, имя и телефон остаются в state — возвращаемся к выбору тарифа
    await _show_tariffs(callback, state)
    await callback.answer()


@router.callback_query(BookingStates.confirm, ConfirmCb.filter(F.ok == True))  # noqa: E712
async def confirm_yes(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    console, tariff_type, duration = data["console"], data["tariff_type"], data["duration"]
    start = datetime.fromisoformat(data["start"])
    end = schedule.calc_end(start, tariff_type, duration)
    price = calc_price(tariff_type, duration)
    current = now()

    booking_id = None
    if schedule.is_valid_start(start, current):
        booking_id = await db.create_booking_if_free(
            user_id=callback.from_user.id, full_name=data["full_name"], phone=data["phone"],
            console=console, tariff_type=tariff_type, duration=duration,
            start_at=start, end_at=end, price=price, units=CONSOLE_UNITS[console], now=current,
        )
    if booking_id is None:
        await callback.answer()
        await _show_dates(callback, state, db,
                          prefix="😔 Пока вы оформляли запись, это время заняли. Выберите другое.\n\n")
        return

    await state.clear()
    summary = booking_summary(console, data["full_name"], data["phone"], tariff_type, duration,
                              start, end, price)
    await edit_or_send(callback, "✅ <b>Вы успешно записались!</b>\n\n" + summary)
    await callback.answer("Вы успешно записались!")
    await callback.bot.send_message(callback.from_user.id, content.WELCOME_TEXT,
                                    reply_markup=kb.main_menu())

    user = callback.from_user
    username = f" (@{user.username})" if user.username else ""
    await notify_admin(
        callback.bot,
        f"🆕 <b>Новая бронь #{booking_id}</b>\n"
        f"Клиент: <a href=\"tg://user?id={user.id}\">{user.id}</a>{username}\n\n" + summary,
    )
