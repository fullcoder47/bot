from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin_common import (
    require_company_admin_callback,
    require_company_admin_message,
    show_company_admin_panel,
)
from app.bot.keyboards.inline.company_admin_settings import (
    build_company_admin_language_keyboard,
    build_company_admin_settings_keyboard,
    build_company_admin_settings_navigation_keyboard,
)
from app.bot.keyboards.reply.company_admin import (
    back_button_texts,
    branches_button_texts,
    build_branch_menu_keyboard,
    build_company_admin_flow_back_keyboard,
    build_department_menu_keyboard,
    build_employee_menu_keyboard,
    build_shift_menu_keyboard,
    departments_button_texts,
    employees_button_texts,
    shifts_button_texts,
)
from app.bot.states.company_admin_settings_states import CompanyAdminSettingsStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import CompanyAdminAccessDTO, CompanyDetailDTO
from app.domain.enums.language import LanguageCode
from app.domain.exceptions.company_admin_exceptions import InvalidPhoneError
from app.services.auth_service import AuthService
from app.services.company_admin_settings_service import CompanyAdminSettingsService
from app.services.stats_service import StatsService

router = Router(name="company_admin")


def _language_name(language_code: LanguageCode | None) -> str:
    mapping = {
        LanguageCode.UZ: "O'zbekcha",
        LanguageCode.RU: "Русский",
        LanguageCode.EN: "English",
    }
    return mapping.get(language_code or DEFAULT_LANGUAGE, "O'zbekcha")


def _format_company_admin_settings_overview(
    access: CompanyAdminAccessDTO,
    company: CompanyDetailDTO,
    *,
    total_employees: int,
) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    status_text = t(
        language,
        uz="Faol" if company.is_active else "Nofaol",
        ru="Активна" if company.is_active else "Неактивна",
        en="Active" if company.is_active else "Inactive",
    )
    subscription_text = company.subscription_end.strftime("%Y-%m-%d") if company.subscription_end else "-"

    return "\n".join(
        [
            t(language, uz="Sozlamalar bo'limi", ru="Раздел настроек", en="Settings section"),
            t(
                language,
                uz=f"🌐 Joriy til: {_language_name(access.user.language)}",
                ru=f"🌐 Текущий язык: {_language_name(access.user.language)}",
                en=f"🌐 Current language: {_language_name(access.user.language)}",
            ),
            t(
                language,
                uz=f"📱 Kontakt telefon: {access.user.phone or '-'}",
                ru=f"📱 Контактный телефон: {access.user.phone or '-'}",
                en=f"📱 Contact phone: {access.user.phone or '-'}",
            ),
            t(
                language,
                uz=f"🏢 Kompaniya: {company.name}",
                ru=f"🏢 Компания: {company.name}",
                en=f"🏢 Company: {company.name}",
            ),
            t(
                language,
                uz=f"💳 Tarif: {company.plan.value}",
                ru=f"💳 Тариф: {company.plan.value}",
                en=f"💳 Plan: {company.plan.value}",
            ),
            t(
                language,
                uz=f"🔁 Holat: {status_text}",
                ru=f"🔁 Статус: {status_text}",
                en=f"🔁 Status: {status_text}",
            ),
            t(
                language,
                uz=f"📅 Subscription tugashi: {subscription_text}",
                ru=f"📅 Окончание подписки: {subscription_text}",
                en=f"📅 Subscription end: {subscription_text}",
            ),
            t(
                language,
                uz=f"👤 Biriktirilgan admin Telegram ID: {company.assigned_admin_telegram_id or '-'}",
                ru=f"👤 Telegram ID назначенного админа: {company.assigned_admin_telegram_id or '-'}",
                en=f"👤 Assigned admin Telegram ID: {company.assigned_admin_telegram_id or '-'}",
            ),
            t(
                language,
                uz=f"👥 Jami ishchilar: {total_employees}",
                ru=f"👥 Всего сотрудников: {total_employees}",
                en=f"👥 Total employees: {total_employees}",
            ),
            "",
            t(
                language,
                uz="Pastdagi tugmalar orqali til, kontakt telefon va profil ma'lumotlarini boshqaring.",
                ru="Управляйте языком, контактным телефоном и информацией профиля с помощью кнопок ниже.",
                en="Use the buttons below to manage language, contact phone, and profile information.",
            ),
        ]
    )


def _format_company_admin_profile(access: CompanyAdminAccessDTO) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    username = f"@{access.user.username}" if access.user.username else "-"
    return "\n".join(
        [
            t(language, uz="Profil ma'lumotlari", ru="Информация профиля", en="Profile information"),
            t(
                language,
                uz=f"👤 F.I.Sh: {access.user.full_name}",
                ru=f"👤 Ф.И.О.: {access.user.full_name}",
                en=f"👤 Full name: {access.user.full_name}",
            ),
            t(
                language,
                uz=f"🆔 Telegram ID: {access.user.telegram_id}",
                ru=f"🆔 Telegram ID: {access.user.telegram_id}",
                en=f"🆔 Telegram ID: {access.user.telegram_id}",
            ),
            t(
                language,
                uz=f"🔗 Username: {username}",
                ru=f"🔗 Username: {username}",
                en=f"🔗 Username: {username}",
            ),
            t(
                language,
                uz=f"📱 Kontakt telefon: {access.user.phone or '-'}",
                ru=f"📱 Контактный телефон: {access.user.phone or '-'}",
                en=f"📱 Contact phone: {access.user.phone or '-'}",
            ),
            t(
                language,
                uz=f"🌐 Til: {_language_name(access.user.language)}",
                ru=f"🌐 Язык: {_language_name(access.user.language)}",
                en=f"🌐 Language: {_language_name(access.user.language)}",
            ),
            t(
                language,
                uz=f"🏢 Kompaniya: {access.company.name}",
                ru=f"🏢 Компания: {access.company.name}",
                en=f"🏢 Company: {access.company.name}",
            ),
        ]
    )


def _format_company_admin_company_info(
    access: CompanyAdminAccessDTO,
    company: CompanyDetailDTO,
    *,
    stats_text: str,
) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    status_text = t(
        language,
        uz="Faol" if company.is_active else "Nofaol",
        ru="Активна" if company.is_active else "Неактивна",
        en="Active" if company.is_active else "Inactive",
    )
    assignment_status = (
        t(language, uz="Faol", ru="Активна", en="Active")
        if company.admin_assignment_is_active
        else t(language, uz="Nofaol", ru="Неактивна", en="Inactive")
        if company.has_admin_assignment
        else "-"
    )
    subscription_text = company.subscription_end.strftime("%Y-%m-%d") if company.subscription_end else "-"
    return "\n".join(
        [
            t(language, uz="Kompaniya ma'lumotlari", ru="Информация о компании", en="Company information"),
            t(
                language,
                uz=f"🏢 Nomi: {company.name}",
                ru=f"🏢 Название: {company.name}",
                en=f"🏢 Name: {company.name}",
            ),
            t(
                language,
                uz=f"💳 Tarif: {company.plan.value}",
                ru=f"💳 Тариф: {company.plan.value}",
                en=f"💳 Plan: {company.plan.value}",
            ),
            t(
                language,
                uz=f"🔁 Holati: {status_text}",
                ru=f"🔁 Статус: {status_text}",
                en=f"🔁 Status: {status_text}",
            ),
            t(
                language,
                uz=f"📅 Subscription tugashi: {subscription_text}",
                ru=f"📅 Окончание подписки: {subscription_text}",
                en=f"📅 Subscription end: {subscription_text}",
            ),
            t(
                language,
                uz=f"👤 Company admin Telegram ID: {company.assigned_admin_telegram_id or '-'}",
                ru=f"👤 Telegram ID company admin: {company.assigned_admin_telegram_id or '-'}",
                en=f"👤 Company admin Telegram ID: {company.assigned_admin_telegram_id or '-'}",
            ),
            t(
                language,
                uz=f"🪪 Biriktirish holati: {assignment_status}",
                ru=f"🪪 Статус назначения: {assignment_status}",
                en=f"🪪 Assignment status: {assignment_status}",
            ),
            "",
            stats_text,
        ]
    )


def _format_company_stats_summary(
    access: CompanyAdminAccessDTO,
    *,
    total_employees: int,
    active_employees: int,
    inactive_employees: int,
    total_branches: int,
    total_departments: int,
    total_shifts: int,
) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    return "\n".join(
        [
            t(language, uz="Kompaniya statistikasi", ru="Статистика компании", en="Company statistics"),
            t(
                language,
                uz=f"👥 Jami ishchilar: {total_employees}",
                ru=f"👥 Всего сотрудников: {total_employees}",
                en=f"👥 Total employees: {total_employees}",
            ),
            t(
                language,
                uz=f"✅ Faol ishchilar: {active_employees}",
                ru=f"✅ Активные сотрудники: {active_employees}",
                en=f"✅ Active employees: {active_employees}",
            ),
            t(
                language,
                uz=f"⛔ Nofaol ishchilar: {inactive_employees}",
                ru=f"⛔ Неактивные сотрудники: {inactive_employees}",
                en=f"⛔ Inactive employees: {inactive_employees}",
            ),
            t(
                language,
                uz=f"🏢 Jami filiallar: {total_branches}",
                ru=f"🏢 Всего филиалов: {total_branches}",
                en=f"🏢 Total branches: {total_branches}",
            ),
            t(
                language,
                uz=f"🗂 Jami bo'limlar: {total_departments}",
                ru=f"🗂 Всего отделов: {total_departments}",
                en=f"🗂 Total departments: {total_departments}",
            ),
            t(
                language,
                uz=f"⏰ Jami smenalar: {total_shifts}",
                ru=f"⏰ Всего смен: {total_shifts}",
                en=f"⏰ Total shifts: {total_shifts}",
            ),
        ]
    )


async def _reload_company_admin_access(
    telegram_id: int,
    session: AsyncSession,
    settings: Settings,
) -> CompanyAdminAccessDTO:
    return await AuthService(session, settings).require_company_admin(telegram_id)


async def _build_settings_context(
    access: CompanyAdminAccessDTO,
    session: AsyncSession,
) -> tuple[CompanyDetailDTO, str, int]:
    settings_service = CompanyAdminSettingsService(session)
    stats = await StatsService(session).get_company_admin_statistics(access.company.id)
    company = await settings_service.get_company_detail(access.company.id)
    stats_text = _format_company_stats_summary(
        access,
        total_employees=stats.total_employees,
        active_employees=stats.active_employees,
        inactive_employees=stats.inactive_employees,
        total_branches=stats.total_branches,
        total_departments=stats.total_departments,
        total_shifts=stats.total_shifts,
    )
    return company, stats_text, stats.total_employees


async def show_employee_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Ishchilar menyusi", ru="Меню сотрудников", en="Employees menu"),
        reply_markup=build_employee_menu_keyboard(language or DEFAULT_LANGUAGE),
    )


async def show_branch_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Filiallar menyusi", ru="Меню филиалов", en="Branches menu"),
        reply_markup=build_branch_menu_keyboard(language or DEFAULT_LANGUAGE),
    )


async def show_department_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Bo'limlar menyusi", ru="Меню отделов", en="Departments menu"),
        reply_markup=build_department_menu_keyboard(language or DEFAULT_LANGUAGE),
    )


async def show_shift_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Smenalar menyusi", ru="Меню смен", en="Shifts menu"),
        reply_markup=build_shift_menu_keyboard(language or DEFAULT_LANGUAGE),
    )


async def show_company_admin_settings_menu(
    message: Message,
    access: CompanyAdminAccessDTO,
    session: AsyncSession,
) -> None:
    company, _, total_employees = await _build_settings_context(access, session)
    await message.answer(
        _format_company_admin_settings_overview(
            access,
            company,
            total_employees=total_employees,
        ),
        reply_markup=build_company_admin_settings_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


async def _edit_company_admin_settings_menu(
    message: Message,
    access: CompanyAdminAccessDTO,
    session: AsyncSession,
) -> None:
    company, _, total_employees = await _build_settings_context(access, session)
    await message.edit_text(
        _format_company_admin_settings_overview(
            access,
            company,
            total_employees=total_employees,
        ),
        reply_markup=build_company_admin_settings_keyboard(access.user.language or DEFAULT_LANGUAGE),
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


@router.message(CompanyAdminSettingsStates.waiting_for_phone, LocalizedTextFilter(*back_button_texts()))
async def company_admin_settings_phone_back_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_company_admin_settings_menu(message, access, session)


@router.message(CompanyAdminSettingsStates.waiting_for_phone)
async def company_admin_settings_phone_input_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return

    settings_service = CompanyAdminSettingsService(session)
    try:
        phone = settings_service.parse_optional_phone(message.text or "")
    except InvalidPhoneError:
        await message.answer(
            t(
                access.user.language,
                uz="Telefon raqami noto'g'ri. Masalan: +998901234567 yoki `-` yuboring.",
                ru="Некорректный номер телефона. Например: +998901234567 или отправьте `-`.",
                en="Invalid phone number. Example: +998901234567 or send `-`.",
            )
        )
        return

    await settings_service.update_phone(
        access.user.telegram_id,
        phone,
        actor_telegram_id=access.user.telegram_id,
    )
    await state.clear()
    refreshed_access = await _reload_company_admin_access(access.user.telegram_id, session, settings)
    await message.answer(
        t(
            refreshed_access.user.language,
            uz="Kontakt telefon yangilandi.",
            ru="Контактный телефон обновлён.",
            en="Contact phone updated.",
        )
    )
    await show_company_admin_settings_menu(message, refreshed_access, session)


@router.callback_query(F.data == "companyadmin:settings:menu")
async def company_admin_settings_menu_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await _edit_company_admin_settings_menu(callback.message, access, session)


@router.callback_query(F.data == "companyadmin:settings:language")
async def company_admin_settings_language_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await callback.message.edit_text(
        t(
            access.user.language,
            uz="Kerakli tilni tanlang.",
            ru="Выберите нужный язык.",
            en="Choose the desired language.",
        ),
        reply_markup=build_company_admin_language_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data.startswith("companyadmin:settings:language:set:"))
async def company_admin_settings_language_set_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return

    raw_language = callback.data.rsplit(":", 1)[-1]
    try:
        target_language = LanguageCode(raw_language)
    except ValueError:
        await callback.answer(
            t(
                access.user.language,
                uz="Noto'g'ri til tanlandi.",
                ru="Выбран некорректный язык.",
                en="An invalid language was selected.",
            ),
            show_alert=True,
        )
        return

    if access.user.language == target_language:
        await callback.answer(
            t(
                access.user.language,
                uz="Bu til allaqachon tanlangan.",
                ru="Этот язык уже выбран.",
                en="This language is already selected.",
            )
        )
        await callback.message.edit_text(
            t(
                access.user.language,
                uz="Kerakli tilni tanlang.",
                ru="Выберите нужный язык.",
                en="Choose the desired language.",
            ),
            reply_markup=build_company_admin_language_keyboard(
                access.user.language or DEFAULT_LANGUAGE,
                access.user.language or DEFAULT_LANGUAGE,
            ),
        )
        return

    settings_service = CompanyAdminSettingsService(session)
    await settings_service.update_language(
        access.user.telegram_id,
        target_language,
        actor_telegram_id=access.user.telegram_id,
    )
    refreshed_access = await _reload_company_admin_access(access.user.telegram_id, session, settings)

    await callback.answer(
        t(
            refreshed_access.user.language,
            uz="Til muvaffaqiyatli yangilandi.",
            ru="Язык успешно обновлён.",
            en="Language updated successfully.",
        )
    )
    await callback.message.edit_text(
        t(
            refreshed_access.user.language,
            uz="Til yangilandi. Sozlamalar menyusi ham yangilandi.",
            ru="Язык обновлён. Меню настроек тоже обновлено.",
            en="Language updated. The settings menu has been refreshed as well.",
        ),
        reply_markup=build_company_admin_settings_navigation_keyboard(
            refreshed_access.user.language or DEFAULT_LANGUAGE,
        ),
    )
    await show_company_admin_panel(callback.message, refreshed_access, session)
    await show_company_admin_settings_menu(callback.message, refreshed_access, session)


@router.callback_query(F.data == "companyadmin:settings:phone")
async def company_admin_settings_phone_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await state.set_state(CompanyAdminSettingsStates.waiting_for_phone)
    await callback.answer()
    await callback.message.answer(
        t(
            access.user.language,
            uz="Yangi kontakt telefonni yuboring. O'chirish uchun `-` yuboring.",
            ru="Отправьте новый контактный телефон. Чтобы очистить, отправьте `-`.",
            en="Send the new contact phone. Send `-` to clear it.",
        ),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.callback_query(F.data == "companyadmin:settings:profile")
async def company_admin_settings_profile_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_company_admin_profile(access),
        reply_markup=build_company_admin_settings_navigation_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data == "companyadmin:settings:company")
async def company_admin_settings_company_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return

    company, stats_text, _ = await _build_settings_context(access, session)
    await callback.answer()
    await callback.message.edit_text(
        _format_company_admin_company_info(access, company, stats_text=stats_text),
        reply_markup=build_company_admin_settings_navigation_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data == "companyadmin:settings:refresh")
async def company_admin_settings_refresh_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer(
        t(
            access.user.language,
            uz="Sozlamalar yangilandi.",
            ru="Настройки обновлены.",
            en="Settings refreshed.",
        )
    )
    await _edit_company_admin_settings_menu(callback.message, access, session)


@router.callback_query(F.data == "companyadmin:settings:back")
async def company_admin_settings_back_handler(
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
        t(
            access.user.language,
            uz="Company admin paneliga qaytdingiz.",
            ru="Вы вернулись в панель company admin.",
            en="You are back in the company admin panel.",
        )
    )
    await show_company_admin_panel(callback.message, access, session)
