from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def check_in_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📍 Ishga keldim", ru="📍 Я пришел на работу", en="📍 I arrived at work")


def check_out_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🏁 Ishdan ketdim", ru="🏁 Я ушел с работы", en="🏁 I left work")


def today_status_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📅 Bugungi holatim", ru="📅 Мой статус сегодня", en="📅 My status today")


def history_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🕘 Tarixim", ru="🕘 Моя история", en="🕘 My history")


def leave_request_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📝 Ta'til so'rash", ru="📝 Запросить отпуск", en="📝 Request leave")


def rules_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="ℹ️ Qoidalar", ru="ℹ️ Правила", en="ℹ️ Rules")


def cancel_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="❌ Bekor qilish", ru="❌ Отмена", en="❌ Cancel")


def share_location_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📍 Joylashuv yuborish", ru="📍 Отправить локацию", en="📍 Send location")


def build_employee_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=check_in_button_text(language)),
                KeyboardButton(text=check_out_button_text(language)),
            ],
            [
                KeyboardButton(text=today_status_button_text(language)),
                KeyboardButton(text=history_button_text(language)),
            ],
            [
                KeyboardButton(text=leave_request_button_text(language)),
                KeyboardButton(text=rules_button_text(language)),
            ],
        ],
        resize_keyboard=True,
    )


def build_employee_location_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=share_location_button_text(language), request_location=True)],
            [KeyboardButton(text=cancel_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_employee_cancel_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cancel_button_text(language))]],
        resize_keyboard=True,
    )


def _localized_variants(builder) -> set[str]:
    return {
        builder(LanguageCode.UZ),
        builder(LanguageCode.RU),
        builder(LanguageCode.EN),
    }


def check_in_button_texts() -> set[str]:
    return _localized_variants(check_in_button_text)


def check_out_button_texts() -> set[str]:
    return _localized_variants(check_out_button_text)


def today_status_button_texts() -> set[str]:
    return _localized_variants(today_status_button_text)


def history_button_texts() -> set[str]:
    return _localized_variants(history_button_text)


def leave_request_button_texts() -> set[str]:
    return _localized_variants(leave_request_button_text)


def rules_button_texts() -> set[str]:
    return _localized_variants(rules_button_text)


def cancel_button_texts() -> set[str]:
    return _localized_variants(cancel_button_text)
