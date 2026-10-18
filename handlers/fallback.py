"""Обработка всего, что не подошло под другие хендлеры. Подключается последним."""
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import content
from keyboards import inline as kb

router = Router(name="fallback")


@router.callback_query()
async def stale_button(callback: CallbackQuery) -> None:
    await callback.answer(
        "Эта кнопка больше не активна. Продолжите в последнем сообщении или нажмите /start.",
        show_alert=True,
    )


@router.message()
async def unexpected_message(message: Message, state: FSMContext) -> None:
    if await state.get_state() is not None:
        await message.answer("Пожалуйста, выберите вариант с помощью кнопок выше 👆",
                             reply_markup=kb.home_only())
        return
    await message.answer(content.WELCOME_TEXT, reply_markup=kb.main_menu())
