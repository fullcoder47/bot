from aiogram.fsm.state import State, StatesGroup


class ShiftCreateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_late_after = State()
    waiting_for_early_before = State()
    waiting_for_work_days = State()
    waiting_for_confirmation = State()


class ShiftEditStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_late_after = State()
    waiting_for_early_before = State()
    waiting_for_work_days = State()
    waiting_for_confirmation = State()
