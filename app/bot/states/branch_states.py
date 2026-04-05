from aiogram.fsm.state import State, StatesGroup


class BranchCreateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_latitude = State()
    waiting_for_longitude = State()
    waiting_for_radius = State()
    waiting_for_strict = State()
    waiting_for_confirmation = State()


class BranchEditStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_confirmation = State()


class BranchLocationStates(StatesGroup):
    waiting_for_latitude = State()
    waiting_for_longitude = State()
    waiting_for_radius = State()
    waiting_for_strict = State()
    waiting_for_confirmation = State()
