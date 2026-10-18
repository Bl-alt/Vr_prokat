"""Общие помощники для хендлеров."""
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, TIMEZONE

log = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now(TIMEZONE)


async def edit_or_send(callback: CallbackQuery, text: str,
                       markup: InlineKeyboardMarkup | None = None) -> None:
    """Редактирует сообщение с кнопкой; если это невозможно — отправляет новое."""
    msg = callback.message
    if isinstance(msg, Message):
        try:
            await msg.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            log.debug("Не удалось отредактировать сообщение: %s", e)
    await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)


async def notify_admin(bot: Bot, text: str) -> None:
    if ADMIN_CHAT_ID is None:
        log.warning("ADMIN_CHAT_ID не задан — уведомление не отправлено")
        return
    try:
        await bot.send_message(ADMIN_CHAT_ID, text)
    except TelegramAPIError:
        log.exception("Не удалось отправить уведомление администратору")
