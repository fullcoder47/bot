from aiogram.fsm.state import State, StatesGroup


class CompanyCreateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_plan = State()


class CompanyAdminAssignStates(StatesGroup):
    waiting_for_telegram_id = State()
