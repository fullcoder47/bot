from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def add_company_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="➕ Kompaniya qo'shish",
        ru="➕ Добавить компанию",
        en="➕ Add company",
    )


def company_list_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="📋 Kompaniyalar ro'yxati",
        ru="📋 Список компаний",
        en="📋 Company list",
    )


def company_menu_back_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="⬅️ Orqaga",
        ru="⬅️ Назад",
        en="⬅️ Back",
    )


def build_super_admin_company_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=add_company_button_text(language))],
            [KeyboardButton(text=company_list_button_text(language))],
            [KeyboardButton(text=company_menu_back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_company_flow_back_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=company_menu_back_button_text(language))]],
        resize_keyboard=True,
    )


def add_company_button_texts() -> set[str]:
    return {
        add_company_button_text(LanguageCode.UZ),
        add_company_button_text(LanguageCode.RU),
        add_company_button_text(LanguageCode.EN),
    }


def company_list_button_texts() -> set[str]:
    return {
        company_list_button_text(LanguageCode.UZ),
        company_list_button_text(LanguageCode.RU),
        company_list_button_text(LanguageCode.EN),
    }


def company_menu_back_button_texts() -> set[str]:
    return {
        company_menu_back_button_text(LanguageCode.UZ),
        company_menu_back_button_text(LanguageCode.RU),
        company_menu_back_button_text(LanguageCode.EN),
    }
