from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def marked(selected: bool, text: str) -> str:
    return f"• {text}" if selected else text


def build_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Tasdiqlash", ru="✅ Подтвердить", en="✅ Confirm"),
                    callback_data=confirm_callback,
                ),
                InlineKeyboardButton(
                    text=t(language, uz="❌ Bekor qilish", ru="❌ Отмена", en="❌ Cancel"),
                    callback_data=cancel_callback,
                ),
            ]
        ]
    )


def build_yes_no_keyboard(
    yes_callback: str,
    no_callback: str,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Ha", ru="✅ Да", en="✅ Yes"),
                    callback_data=yes_callback,
                ),
                InlineKeyboardButton(
                    text=t(language, uz="❌ Yo'q", ru="❌ Нет", en="❌ No"),
                    callback_data=no_callback,
                ),
            ]
        ]
    )
