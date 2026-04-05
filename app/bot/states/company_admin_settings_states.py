from aiogram.fsm.state import State, StatesGroup


class CompanyAdminSettingsStates(StatesGroup):
    waiting_for_phone = State()
