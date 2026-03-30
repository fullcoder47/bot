from aiogram.fsm.state import State, StatesGroup


class CompanyCreateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_plan = State()
    waiting_for_confirmation = State()


class CompanyEditStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_confirmation = State()


class CompanyAdminAssignStates(StatesGroup):
    waiting_for_telegram_id = State()
    waiting_for_confirmation = State()


class CompanySubscriptionStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_confirmation = State()


class CompanySearchStates(StatesGroup):
    waiting_for_query = State()


class CompanyDeleteStates(StatesGroup):
    waiting_for_confirmation = State()
