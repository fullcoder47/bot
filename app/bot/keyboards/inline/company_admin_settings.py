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


def build_company_admin_settings_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="🌐 Til", ru="🌐 Язык", en="🌐 Language"),
                    callback_data="companyadmin:settings:language",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="📱 Kontakt telefon", ru="📱 Контактный телефон", en="📱 Contact phone"),
                    callback_data="companyadmin:settings:phone",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="👤 Profilim", ru="👤 Мой профиль", en="👤 My profile"),
                    callback_data="companyadmin:settings:profile",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🏢 Kompaniya ma'lumoti", ru="🏢 Информация о компании", en="🏢 Company info"),
                    callback_data="companyadmin:settings:company",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🔄 Yangilash", ru="🔄 Обновить", en="🔄 Refresh"),
                    callback_data="companyadmin:settings:refresh",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="companyadmin:settings:back",
                )
            ],
        ]
    )


def build_company_admin_language_keyboard(
    current_language: LanguageCode | str | None,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.UZ),
                    callback_data="companyadmin:settings:language:set:uz",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.RU),
                    callback_data="companyadmin:settings:language:set:ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_language_button_label(current_language, LanguageCode.EN),
                    callback_data="companyadmin:settings:language:set:en",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Sozlamalarga", ru="⬅️ К настройкам", en="⬅️ To settings"),
                    callback_data="companyadmin:settings:menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="companyadmin:settings:back",
                )
            ],
        ]
    )


def build_company_admin_settings_navigation_keyboard(
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Sozlamalarga", ru="⬅️ К настройкам", en="⬅️ To settings"),
                    callback_data="companyadmin:settings:menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ Вернуться в панель", en="⬅️ Back to panel"),
                    callback_data="companyadmin:settings:back",
                )
            ],
        ]
    )
