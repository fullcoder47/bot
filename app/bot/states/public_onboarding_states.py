from aiogram.fsm.state import State, StatesGroup


class PublicOnboardingStates(StatesGroup):
    waiting_for_receipt_photo = State()
    waiting_for_company_name = State()
    waiting_for_company_plan = State()
    waiting_for_contact_phone = State()
