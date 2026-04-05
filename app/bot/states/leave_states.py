from aiogram.fsm.state import State, StatesGroup


class LeaveRequestStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_from_date = State()
    waiting_for_to_date = State()
    waiting_for_reason = State()
    waiting_for_confirmation = State()
