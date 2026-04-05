from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.localization import t
from app.domain.enums.language import LanguageCode


def employees_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="👥 Ishchilar", ru="👥 Сотрудники", en="👥 Employees")


def branches_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🏢 Filiallar", ru="🏢 Филиалы", en="🏢 Branches")


def departments_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🗂 Bo'limlar", ru="🗂 Отделы", en="🗂 Departments")


def shifts_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="⏰ Smenalar", ru="⏰ Смены", en="⏰ Shifts")


def statistics_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📊 Statistika", ru="📊 Статистика", en="📊 Statistics")


def settings_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="⚙️ Sozlamalar", ru="⚙️ Настройки", en="⚙️ Settings")


def back_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back")


def share_location_button_text(language: LanguageCode | str | None) -> str:
    return t(
        language,
        uz="📍 Joylashuv ulashish",
        ru="📍 Отправить локацию",
        en="📍 Share location",
    )


def add_employee_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="➕ Ishchi qo'shish", ru="➕ Добавить сотрудника", en="➕ Add employee")


def employee_list_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📋 Ishchilar ro'yxati", ru="📋 Список сотрудников", en="📋 Employee list")


def employee_search_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🔎 Qidirish", ru="🔎 Поиск", en="🔎 Search")


def employee_filters_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="🧭 Filterlar", ru="🧭 Фильтры", en="🧭 Filters")


def add_branch_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="➕ Filial qo'shish", ru="➕ Добавить филиал", en="➕ Add branch")


def branch_list_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📋 Filiallar ro'yxati", ru="📋 Список филиалов", en="📋 Branch list")


def add_department_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="➕ Bo'lim qo'shish", ru="➕ Добавить отдел", en="➕ Add department")


def department_list_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📋 Bo'limlar ro'yxati", ru="📋 Список отделов", en="📋 Department list")


def add_shift_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="➕ Smena qo'shish", ru="➕ Добавить смену", en="➕ Add shift")


def shift_list_button_text(language: LanguageCode | str | None) -> str:
    return t(language, uz="📋 Smenalar ro'yxati", ru="📋 Список смен", en="📋 Shift list")


def build_company_admin_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=employees_button_text(language)),
                KeyboardButton(text=branches_button_text(language)),
            ],
            [
                KeyboardButton(text=departments_button_text(language)),
                KeyboardButton(text=shifts_button_text(language)),
            ],
            [
                KeyboardButton(text=statistics_button_text(language)),
                KeyboardButton(text=settings_button_text(language)),
            ],
        ],
        resize_keyboard=True,
    )


def build_employee_menu_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=add_employee_button_text(language)),
                KeyboardButton(text=employee_list_button_text(language)),
            ],
            [
                KeyboardButton(text=employee_search_button_text(language)),
                KeyboardButton(text=employee_filters_button_text(language)),
            ],
            [KeyboardButton(text=back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_branch_menu_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=add_branch_button_text(language)),
                KeyboardButton(text=branch_list_button_text(language)),
            ],
            [KeyboardButton(text=back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_department_menu_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=add_department_button_text(language)),
                KeyboardButton(text=department_list_button_text(language)),
            ],
            [KeyboardButton(text=back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_shift_menu_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=add_shift_button_text(language)),
                KeyboardButton(text=shift_list_button_text(language)),
            ],
            [KeyboardButton(text=back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def build_company_admin_flow_back_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=back_button_text(language))]],
        resize_keyboard=True,
    )


def build_branch_location_input_keyboard(language: LanguageCode | str | None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=share_location_button_text(language), request_location=True)],
            [KeyboardButton(text=back_button_text(language))],
        ],
        resize_keyboard=True,
    )


def _localized_variants(builder) -> set[str]:
    return {
        builder(LanguageCode.UZ),
        builder(LanguageCode.RU),
        builder(LanguageCode.EN),
    }


def employees_button_texts() -> set[str]:
    return _localized_variants(employees_button_text)


def branches_button_texts() -> set[str]:
    return _localized_variants(branches_button_text)


def departments_button_texts() -> set[str]:
    return _localized_variants(departments_button_text)


def shifts_button_texts() -> set[str]:
    return _localized_variants(shifts_button_text)


def statistics_button_texts() -> set[str]:
    return _localized_variants(statistics_button_text)


def settings_button_texts() -> set[str]:
    return _localized_variants(settings_button_text)


def back_button_texts() -> set[str]:
    return _localized_variants(back_button_text)


def add_employee_button_texts() -> set[str]:
    return _localized_variants(add_employee_button_text)


def employee_list_button_texts() -> set[str]:
    return _localized_variants(employee_list_button_text)


def employee_search_button_texts() -> set[str]:
    return _localized_variants(employee_search_button_text)


def employee_filters_button_texts() -> set[str]:
    return _localized_variants(employee_filters_button_text)


def add_branch_button_texts() -> set[str]:
    return _localized_variants(add_branch_button_text)


def branch_list_button_texts() -> set[str]:
    return _localized_variants(branch_list_button_text)


def add_department_button_texts() -> set[str]:
    return _localized_variants(add_department_button_text)


def department_list_button_texts() -> set[str]:
    return _localized_variants(department_list_button_text)


def add_shift_button_texts() -> set[str]:
    return _localized_variants(add_shift_button_text)


def shift_list_button_texts() -> set[str]:
    return _localized_variants(shift_list_button_text)
