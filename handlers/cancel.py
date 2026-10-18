"""Отмена записи."""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import content
from db.database import ACTIVE, Database
from handlers.utils import edit_or_send, notify_admin, now
from keyboards import inline as kb
from keyboards.callbacks import CancelConfirmCb, CancelPickCb, MenuCb
from services.formatting import booking_summary

router = Router(name="cancel")


def _summary(b) -> str:
    return booking_summary(b.console, b.full_name, b.phone, b.tariff_type, b.duration,
                           b.start_at, b.end_at, b.price)


async def _show_list(callback: CallbackQuery, db: Database, prefix: str = "") -> None:
    bookings = await db.user_future_bookings(callback.from_user.id, now())
    if not bookings:
        await edit_or_send(callback, prefix + "У вас нет предстоящих записей.\n\n" + content.WELCOME_TEXT,
                           kb.main_menu())
        return
    await edit_or_send(callback, prefix + "Выберите запись, которую хотите отменить:",
                       kb.user_bookings(bookings))


@router.callback_query(MenuCb.filter(F.action == "cancel"))
async def cancel_menu(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await _show_list(callback, db)
    await callback.answer()


@router.callback_query(CancelPickCb.filter())
async def pick_booking(callback: CallbackQuery, callback_data: CancelPickCb, db: Database) -> None:
    b = await db.get_booking(callback_data.booking_id)
    if b is None or b.user_id != callback.from_user.id or b.status != ACTIVE or b.start_at <= now():
        await callback.answer("Эта запись уже недоступна для отмены", show_alert=True)
        await _show_list(callback, db)
        return
    await edit_or_send(
        callback,
        f"{_summary(b)}\n\n❓ <b>Вы точно уверены, что хотите отменить запись?</b>",
        kb.cancel_confirm(b.id),
    )
    await callback.answer()


@router.callback_query(CancelConfirmCb.filter(F.ok == False))  # noqa: E712
async def cancel_no(callback: CallbackQuery) -> None:
    await edit_or_send(callback, content.WELCOME_TEXT, kb.main_menu())
    await callback.answer()


@router.callback_query(CancelConfirmCb.filter(F.ok == True))  # noqa: E712
async def cancel_yes(callback: CallbackQuery, callback_data: CancelConfirmCb, db: Database,
                     bot: Bot) -> None:
    b = await db.cancel_booking(callback_data.booking_id, callback.from_user.id, now())
    if b is None:
        await callback.answer("Эта запись уже недоступна для отмены", show_alert=True)
        await edit_or_send(callback, content.WELCOME_TEXT, kb.main_menu())
        return

    await edit_or_send(callback, "🗑 <b>Запись отменена.</b>\n\n" + _summary(b))
    await callback.answer("Запись отменена")
    await bot.send_message(callback.from_user.id, content.WELCOME_TEXT, reply_markup=kb.main_menu())

    user = callback.from_user
    username = f" (@{user.username})" if user.username else ""
    await notify_admin(
        bot,
        f"❌ <b>Отмена брони #{b.id}</b>\n"
        f"Клиент: <a href=\"tg://user?id={user.id}\">{user.id}</a>{username}\n\n" + _summary(b),
    )
