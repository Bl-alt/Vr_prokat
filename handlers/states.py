from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    console = State()
    name = State()
    phone = State()
    tariff = State()
    duration = State()
    date = State()
    time = State()
    confirm = State()
