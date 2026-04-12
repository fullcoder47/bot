from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.inline.common import marked
from app.core.localization import t
from app.domain.enums.language import LanguageCode


def _language_button_label(
    current_language: LanguageCode | str | None,
    target_language: LanguageCode,
) -> str:
    labels = {
        LanguageCode.UZ: "🇺🇿 O'zbekcha",
        LanguageCode.RU: "🇷🇺 Русский",
        LanguageCode.EN: "🇬🇧 English",
    }
    return marked(current_language == target_language, labels[target_language])


def build_employee_settings_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="🌐 Til", ru="🌐 Язык", en="🌐 Language"),
                    callback_data="employee:settings:language",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="📱 Kontakt telefon", ru="📱 Контактный телефон", en="📱 Contact phone"),
                    callback_data="employee:settings:phone",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="👤 Profilim", ru="👤 Мой профиль", en="👤 My profile"),
                    callback_data="employee:settings:profile",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🏢 Ish joyim", ru="🏢 Моё место работы", en="🏢 My workplace"),
                    callback_data="employee:settings:work",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🔄 Yangilash", ru="🔄 Обновить", en="🔄 Refresh"),
                    callback_data="employee:settings:refresh",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="employee:settings:back",
                )
            ],
        ]
    )


def build_employee_language_keyboard(
    current_language: LanguageCode | str | None,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.UZ),
                    callback_data="employee:settings:language:set:uz",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.RU),
                    callback_data="employee:settings:language:set:ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.EN),
                    callback_data="employee:settings:language:set:en",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Sozlamalarga", ru="⬅️ К настройкам", en="⬅️ To settings"),
                    callback_data="employee:settings:menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="employee:settings:back",
                )
            ],
        ]
    )


def build_employee_settings_navigation_keyboard(
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Sozlamalarga", ru="⬅️ К настройкам", en="⬅️ To settings"),
                    callback_data="employee:settings:menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="employee:settings:back",
                )
            ],
        ]
    )
