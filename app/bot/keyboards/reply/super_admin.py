from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def companies_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="🏢 Kompaniyalar",
        ru="🏢 Компании",
        en="🏢 Companies",
    )


def statistics_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="📊 Statistika",
        ru="📊 Статистика",
        en="📊 Statistics",
    )


def settings_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="⚙️ Sozlamalar",
        ru="⚙️ Настройки",
        en="⚙️ Settings",
    )


def build_super_admin_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=companies_button_text(language))],
            [KeyboardButton(text=statistics_button_text(language))],
            [KeyboardButton(text=settings_button_text(language))],
        ],
        resize_keyboard=True,
    )


def companies_button_texts() -> set[str]:
    return {
        companies_button_text(LanguageCode.UZ),
        companies_button_text(LanguageCode.RU),
        companies_button_text(LanguageCode.EN),
    }


def statistics_button_texts() -> set[str]:
    return {
        statistics_button_text(LanguageCode.UZ),
        statistics_button_text(LanguageCode.RU),
        statistics_button_text(LanguageCode.EN),
    }


def settings_button_texts() -> set[str]:
    return {
        settings_button_text(LanguageCode.UZ),
        settings_button_text(LanguageCode.RU),
        settings_button_text(LanguageCode.EN),
    }
