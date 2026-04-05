from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.department_dto import DepartmentDTO, DepartmentListPageDTO
from app.domain.enums.language import LanguageCode


def build_department_list_keyboard(
    department_page: DepartmentListPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for department in department_page.items:
        status = t(language, uz="Faol" if department.is_active else "Nofaol", ru="Активен" if department.is_active else "Неактивен", en="Active" if department.is_active else "Inactive")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{department.name} ({status})",
                    callback_data=f"department:detail:{department.id}:{department_page.page}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if department_page.page > 1:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"department:list:{department_page.page - 1}",
            )
        )
    if department_page.total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{department_page.page}/{department_page.total_pages}", callback_data="department:noop"))
    if department_page.page < department_page.total_pages:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"department:list:{department_page.page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data="department:menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_department_detail_keyboard(
    department: DepartmentDTO,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"department:edit:{department.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="⛔ Deaktiv qilish" if department.is_active else "✅ Aktiv qilish",
                        ru="⛔ Деактивировать" if department.is_active else "✅ Активировать",
                        en="⛔ Deactivate" if department.is_active else "✅ Activate",
                    ),
                    callback_data=f"department:toggle:{department.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗑 O'chirish", ru="🗑 Удалить", en="🗑 Delete"),
                    callback_data=f"department:delete:{department.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"department:list:{page}",
                )
            ],
        ]
    )
