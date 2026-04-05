from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.attendance_dto import AttendanceHistoryPageDTO
from app.domain.enums.language import LanguageCode


def build_open_session_keyboard(
    session_id: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="❌ Sessionni bekor qilish", ru="❌ Отменить сессию", en="❌ Cancel session"),
                    callback_data=f"attendance:cancel:{session_id}",
                )
            ]
        ]
    )


def build_history_keyboard(
    history_page: AttendanceHistoryPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for record in history_page.items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{record.date.isoformat()} | {record.status.value}",
                    callback_data=f"attendance:history:detail:{record.id}:{history_page.page}",
                )
            ]
        )

    navigation_row: list[InlineKeyboardButton] = []
    if history_page.page > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"attendance:history:page:{history_page.page - 1}",
            )
        )
    if history_page.total_pages > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text=f"{history_page.page}/{history_page.total_pages}",
                callback_data="attendance:history:noop",
            )
        )
    if history_page.page < history_page.total_pages:
        navigation_row.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"attendance:history:page:{history_page.page + 1}",
            )
        )
    if navigation_row:
        rows.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_history_detail_keyboard(
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Tarixga qaytish", ru="⬅️ Назад к истории", en="⬅️ Back to history"),
                    callback_data=f"attendance:history:page:{page}",
                )
            ]
        ]
    )


def build_leave_type_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="🏖 Ta'til", ru="🏖 Отпуск", en="🏖 Vacation"),
                    callback_data="leave:type:VACATION",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🤒 Kasallik", ru="🤒 Больничный", en="🤒 Sick leave"),
                    callback_data="leave:type:SICK",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🧾 Shaxsiy", ru="🧾 Личное", en="🧾 Personal"),
                    callback_data="leave:type:PERSONAL",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="❌ Bekor qilish", ru="❌ Отмена", en="❌ Cancel"),
                    callback_data="leave:cancel",
                )
            ],
        ]
    )


def build_leave_confirmation_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Yuborish", ru="✅ Отправить", en="✅ Submit"),
                    callback_data="leave:confirm",
                ),
                InlineKeyboardButton(
                    text=t(language, uz="❌ Bekor qilish", ru="❌ Отмена", en="❌ Cancel"),
                    callback_data="leave:cancel",
                ),
            ]
        ]
    )
