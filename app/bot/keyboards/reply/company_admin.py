from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def workers_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="👥 Ishchilar",
        ru="👥 Сотрудники",
        en="👥 Employees",
    )


def attendance_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="🕘 Davomat",
        ru="🕘 Посещаемость",
        en="🕘 Attendance",
    )


def settings_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="⚙️ Sozlamalar",
        ru="⚙️ Настройки",
        en="⚙️ Settings",
    )


def build_company_admin_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=workers_button_text(language))],
            [KeyboardButton(text=attendance_button_text(language))],
            [KeyboardButton(text=settings_button_text(language))],
        ],
        resize_keyboard=True,
    )


def workers_button_texts() -> set[str]:
    return {
        workers_button_text(LanguageCode.UZ),
        workers_button_text(LanguageCode.RU),
        workers_button_text(LanguageCode.EN),
    }


def attendance_button_texts() -> set[str]:
    return {
        attendance_button_text(LanguageCode.UZ),
        attendance_button_text(LanguageCode.RU),
        attendance_button_text(LanguageCode.EN),
    }


def settings_button_texts() -> set[str]:
    return {
        settings_button_text(LanguageCode.UZ),
        settings_button_text(LanguageCode.RU),
        settings_button_text(LanguageCode.EN),
    }
