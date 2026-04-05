from aiogram.fsm.state import State, StatesGroup


class EmployeeCreateStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_telegram_id = State()
    waiting_for_employee_code = State()
    waiting_for_position = State()
    waiting_for_branch = State()
    waiting_for_department = State()
    waiting_for_shift = State()
    waiting_for_hire_date = State()
    waiting_for_confirmation = State()


class EmployeeSearchStates(StatesGroup):
    waiting_for_query = State()


class EmployeeEditStates(StatesGroup):
    waiting_for_value = State()
