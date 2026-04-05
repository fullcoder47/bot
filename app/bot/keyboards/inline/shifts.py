from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.shift_dto import ShiftDTO, ShiftListPageDTO
from app.domain.enums.language import LanguageCode


def build_shift_list_keyboard(
    shift_page: ShiftListPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for shift in shift_page.items:
        status = t(language, uz="Faol" if shift.is_active else "Nofaol", ru="Активна" if shift.is_active else "Неактивна", en="Active" if shift.is_active else "Inactive")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{shift.name} ({status})",
                    callback_data=f"shift:detail:{shift.id}:{shift_page.page}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if shift_page.page > 1:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"shift:list:{shift_page.page - 1}",
            )
        )
    if shift_page.total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{shift_page.page}/{shift_page.total_pages}", callback_data="shift:noop"))
    if shift_page.page < shift_page.total_pages:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"shift:list:{shift_page.page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data="shift:menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_shift_detail_keyboard(
    shift: ShiftDTO,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"shift:edit:{shift.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="⛔ Deaktiv qilish" if shift.is_active else "✅ Aktiv qilish",
                        ru="⛔ Деактивировать" if shift.is_active else "✅ Активировать",
                        en="⛔ Deactivate" if shift.is_active else "✅ Activate",
                    ),
                    callback_data=f"shift:toggle:{shift.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗑 O'chirish", ru="🗑 Удалить", en="🗑 Delete"),
                    callback_data=f"shift:delete:{shift.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"shift:list:{page}",
                )
            ],
        ]
    )
