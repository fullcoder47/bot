from aiogram.fsm.state import State, StatesGroup


class DepartmentCreateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_confirmation = State()


class DepartmentEditStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_confirmation = State()
