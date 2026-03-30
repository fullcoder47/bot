from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def build_super_admin_settings_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="🌐 Til", ru="🌐 Язык", en="🌐 Language"),
                    callback_data="superadmin:settings:language",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="🛠 Tizim sozlamalari",
                        ru="🛠 Системные настройки",
                        en="🛠 System settings",
                    ),
                    callback_data="superadmin:settings:system",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data="superadmin:settings:back",
                )
            ],
        ]
    )
