from aiogram.fsm.state import State, StatesGroup


class AttendanceSessionStates(StatesGroup):
    waiting_for_location = State()
    waiting_for_video = State()
