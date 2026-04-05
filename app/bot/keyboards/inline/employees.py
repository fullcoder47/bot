from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.inline.common import marked
from app.core.localization import t
from app.domain.dto.employee_dto import EmployeeDetailDTO, EmployeeFiltersDTO, EmployeeListPageDTO
from app.domain.enums.language import LanguageCode


def build_employee_list_keyboard(
    employee_page: EmployeeListPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for employee in employee_page.items:
        status = t(language, uz="Faol" if employee.is_active else "Nofaol", ru="Активен" if employee.is_active else "Неактивен", en="Active" if employee.is_active else "Inactive")
        branch_name = employee.branch.name if employee.branch else "-"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{employee.full_name} ({branch_name} | {status})",
                    callback_data=f"employee:detail:{employee.id}:{employee_page.page}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if employee_page.page > 1:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"employee:list:{employee_page.page - 1}",
            )
        )
    if employee_page.total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{employee_page.page}/{employee_page.total_pages}", callback_data="employee:noop"))
    if employee_page.page < employee_page.total_pages:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"employee:list:{employee_page.page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data="employee:menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_employee_detail_keyboard(
    employee: EmployeeDetailDTO,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"employee:edit_menu:{employee.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🧩 Biriktirishlarni o'zgartirish", ru="🧩 Изменить привязки", en="🧩 Update assignments"),
                    callback_data=f"employee:assignments:{employee.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="🔁 Deaktiv qilish" if employee.is_active else "🔁 Aktiv qilish",
                        ru="🔁 Деактивировать" if employee.is_active else "🔁 Активировать",
                        en="🔁 Deactivate" if employee.is_active else "🔁 Activate",
                    ),
                    callback_data=f"employee:toggle:{employee.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"employee:list:{page}",
                )
            ],
        ]
    )


def build_employee_edit_menu_keyboard(
    employee_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, uz="👤 F.I.Sh", ru="👤 Ф.И.О.", en="👤 Full name"), callback_data=f"employee:edit_field:{employee_id}:{page}:full_name")],
            [InlineKeyboardButton(text=t(language, uz="📞 Telefon", ru="📞 Телефон", en="📞 Phone"), callback_data=f"employee:edit_field:{employee_id}:{page}:phone")],
            [InlineKeyboardButton(text=t(language, uz="🆔 Telegram ID", ru="🆔 Telegram ID", en="🆔 Telegram ID"), callback_data=f"employee:edit_field:{employee_id}:{page}:telegram_id")],
            [InlineKeyboardButton(text=t(language, uz="🏷 Kod", ru="🏷 Код", en="🏷 Code"), callback_data=f"employee:edit_field:{employee_id}:{page}:employee_code")],
            [InlineKeyboardButton(text=t(language, uz="💼 Lavozim", ru="💼 Должность", en="💼 Position"), callback_data=f"employee:edit_field:{employee_id}:{page}:position")],
            [InlineKeyboardButton(text=t(language, uz="📅 Ishga kirgan sana", ru="📅 Дата найма", en="📅 Hire date"), callback_data=f"employee:edit_field:{employee_id}:{page}:hire_date")],
            [InlineKeyboardButton(text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"), callback_data=f"employee:detail:{employee_id}:{page}")],
        ]
    )


def build_employee_assignment_keyboard(
    employee_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, uz="🏢 Filial", ru="🏢 Филиал", en="🏢 Branch"), callback_data=f"employee:assign_branch:{employee_id}:{page}")],
            [InlineKeyboardButton(text=t(language, uz="🗂 Bo'lim", ru="🗂 Отдел", en="🗂 Department"), callback_data=f"employee:assign_department:{employee_id}:{page}")],
            [InlineKeyboardButton(text=t(language, uz="⏰ Smena", ru="⏰ Смена", en="⏰ Shift"), callback_data=f"employee:assign_shift:{employee_id}:{page}")],
            [InlineKeyboardButton(text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"), callback_data=f"employee:detail:{employee_id}:{page}")],
        ]
    )


def build_employee_filter_keyboard(
    filters: EmployeeFiltersDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=marked(filters.is_active is None, t(language, uz="Barchasi", ru="Все", en="All")), callback_data="employee:filter:status:all"),
            InlineKeyboardButton(text=marked(filters.is_active is True, t(language, uz="Faol", ru="Активные", en="Active")), callback_data="employee:filter:status:active"),
            InlineKeyboardButton(text=marked(filters.is_active is False, t(language, uz="Nofaol", ru="Неактивные", en="Inactive")), callback_data="employee:filter:status:inactive"),
        ],
        [
            InlineKeyboardButton(text=t(language, uz="🏢 Filial", ru="🏢 Филиал", en="🏢 Branch"), callback_data="employee:filter_branch:open"),
            InlineKeyboardButton(text=t(language, uz="🗂 Bo'lim", ru="🗂 Отдел", en="🗂 Department"), callback_data="employee:filter_department:open"),
        ],
        [
            InlineKeyboardButton(text=t(language, uz="⏰ Smena", ru="⏰ Смена", en="⏰ Shift"), callback_data="employee:filter_shift:open"),
            InlineKeyboardButton(text=t(language, uz="🧹 Tozalash", ru="🧹 Очистить", en="🧹 Clear"), callback_data="employee:filter:clear"),
        ],
        [
            InlineKeyboardButton(text=t(language, uz="✅ Qo'llash", ru="✅ Применить", en="✅ Apply"), callback_data="employee:filter:apply"),
            InlineKeyboardButton(text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"), callback_data="employee:menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_option_selection_keyboard(
    options: Sequence[tuple[int, str]],
    *,
    callback_prefix: str,
    language: LanguageCode | str | None,
    back_callback: str,
    allow_skip: bool = False,
    allow_clear: bool = False,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=label, callback_data=f"{callback_prefix}:{entity_id}")]
        for entity_id, label in options
    ]
    if allow_skip:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="⏭ O'tkazib yuborish", ru="⏭ Пропустить", en="⏭ Skip"),
                    callback_data=f"{callback_prefix}:skip",
                )
            ]
        )
    if allow_clear:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="🧹 Tozalash", ru="🧹 Очистить", en="🧹 Clear"),
                    callback_data=f"{callback_prefix}:clear",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data=back_callback,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
