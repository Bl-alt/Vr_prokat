"""/start, главное меню и информационные разделы."""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import content
from handlers.states import BookingStates
from handlers.utils import edit_or_send
from keyboards import inline as kb
from keyboards.callbacks import MenuCb

router = Router(name="common")


async def _leave_phone_step(message: Message, state: FSMContext) -> None:
    """На шаге телефона висит reply-клавиатура — её нужно убрать отдельным сообщением."""
    if await state.get_state() == BookingStates.phone.state:
        await message.answer("Возвращаемся в главное меню.", reply_markup=ReplyKeyboardRemove())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await _leave_phone_step(message, state)
    await state.clear()
    await message.answer(content.WELCOME_TEXT, reply_markup=kb.main_menu())


@router.message(F.text == kb.HOME_TEXT)
async def home_by_text(message: Message, state: FSMContext) -> None:
    await _leave_phone_step(message, state)
    await state.clear()
    await message.answer(content.WELCOME_TEXT, reply_markup=kb.main_menu())


@router.callback_query(MenuCb.filter(F.action == "home"))
async def home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback, content.WELCOME_TEXT, kb.main_menu())
    await callback.answer()


@router.callback_query(MenuCb.filter(F.action == "features"))
async def features(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback, content.FEATURES_TEXT, kb.home_only())
    await callback.answer()


@router.callback_query(MenuCb.filter(F.action == "terms"))
async def terms(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback, content.TERMS_TEXT, kb.home_only())
    await callback.answer()
