from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def build_company_admin_statistics_keyboard(
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="📥 Bugungi Excel", ru="📥 Excel за сегодня", en="📥 Today's Excel"),
                    callback_data="companyadmin:attendance_export:today",
                ),
                InlineKeyboardButton(
                    text=t(language, uz="📆 Oylik Excel", ru="📆 Excel за месяц", en="📆 Monthly Excel"),
                    callback_data="companyadmin:attendance_export:month",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗂 Barcha yozuvlar", ru="🗂 Все записи", en="🗂 All records"),
                    callback_data="companyadmin:attendance_export:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Panelga qaytish", ru="⬅️ В панель", en="⬅️ Back to panel"),
                    callback_data="companyadmin:statistics:back",
                )
            ],
        ]
    )
