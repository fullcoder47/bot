from aiogram.fsm.state import State, StatesGroup


class SuperAdminSettingsStates(StatesGroup):
    waiting_for_payment_card = State()
