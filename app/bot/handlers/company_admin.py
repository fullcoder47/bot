from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.role import RoleFilter
from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin_common import (
    format_company_admin_dashboard,
    require_company_admin_callback,
    require_company_admin_message,
    show_company_admin_panel,
)
from app.bot.keyboards.reply.company_admin import (
    add_branch_button_texts,
    add_department_button_texts,
    add_employee_button_texts,
    add_shift_button_texts,
    back_button_texts,
    branches_button_texts,
    build_branch_menu_keyboard,
    build_company_admin_keyboard,
    build_department_menu_keyboard,
    build_employee_menu_keyboard,
    build_shift_menu_keyboard,
    departments_button_texts,
    employee_filters_button_texts,
    employee_list_button_texts,
    employee_search_button_texts,
    employees_button_texts,
    settings_button_texts,
    shifts_button_texts,
    statistics_button_texts,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.enums.role import UserRole
from app.services.stats_service import StatsService

router = Router(name="company_admin")
router.message.filter(RoleFilter(UserRole.COMPANY_ADMIN))
router.callback_query.filter(RoleFilter(UserRole.COMPANY_ADMIN))


async def show_employee_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Ishchilar menyusi", ru="Меню сотрудников", en="Employees menu"),
        reply_markup=build_employee_menu_keyboard(language),
    )


async def show_branch_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Filiallar menyusi", ru="Меню филиалов", en="Branches menu"),
        reply_markup=build_branch_menu_keyboard(language),
    )


async def show_department_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Bo'limlar menyusi", ru="Меню отделов", en="Departments menu"),
        reply_markup=build_department_menu_keyboard(language),
    )


async def show_shift_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Smenalar menyusi", ru="Меню смен", en="Shifts menu"),
        reply_markup=build_shift_menu_keyboard(language),
    )


@router.message(LocalizedTextFilter(*employees_button_texts()))
async def employees_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_employee_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*branches_button_texts()))
async def branches_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_branch_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*departments_button_texts()))
async def departments_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_department_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*shifts_button_texts()))
async def shifts_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_shift_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*statistics_button_texts()))
async def company_admin_statistics_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    stats = await StatsService(session).get_company_admin_statistics(access.company.id)
    await message.answer(format_company_admin_dashboard(access.user.language, access.company.name, stats))


@router.message(LocalizedTextFilter(*settings_button_texts()))
async def company_admin_settings_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    await message.answer(
        "\n".join(
            [
                t(access.user.language, uz="Sozlamalar bo'limi", ru="Раздел настроек", en="Settings section"),
                t(access.user.language, uz="• Tilni o'zgartirish keyingi bosqichda kengaytiriladi.", ru="• Смена языка будет расширена на следующем этапе.", en="• Change language will be expanded in the next stage."),
                t(access.user.language, uz="• Kompaniya ma'lumotlari bo'limi keyingi bosqichga tayyorlangan.", ru="• Раздел данных компании подготовлен для следующего этапа.", en="• Company information settings are prepared for the next stage."),
            ]
        )
    )


@router.message(
    StateFilter(None),
    LocalizedTextFilter(
        *back_button_texts(),
    ),
)
async def company_admin_back_to_panel_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_company_admin_panel(message, access, session)


@router.callback_query(F.data == "employee:menu")
async def employee_menu_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar menyusiga qayting.", ru="Вернитесь в меню сотрудников.", en="Return to the employees menu.")
    )
    await show_employee_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "branch:menu")
async def branch_menu_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Filiallar menyusiga qayting.", ru="Вернитесь в меню филиалов.", en="Return to the branches menu.")
    )
    await show_branch_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "department:menu")
async def department_menu_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Bo'limlar menyusiga qayting.", ru="Вернитесь в меню отделов.", en="Return to the departments menu.")
    )
    await show_department_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "shift:menu")
async def shift_menu_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Smenalar menyusiga qayting.", ru="Вернитесь в меню смен.", en="Return to the shifts menu.")
    )
    await show_shift_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)
