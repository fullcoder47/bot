from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.employee_common import (
    require_employee_callback,
    require_employee_message,
    show_employee_panel,
)
from app.bot.keyboards.inline.employee_settings import (
    build_employee_language_keyboard,
    build_employee_settings_keyboard,
    build_employee_settings_navigation_keyboard,
)
from app.bot.keyboards.reply.employee import (
    build_employee_keyboard,
    rules_button_texts,
    settings_button_texts,
)
from app.bot.states.employee_settings_states import EmployeeSettingsStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.enums.language import LanguageCode
from app.domain.exceptions.company_admin_exceptions import InvalidPhoneError
from app.services.auth_service import AuthService
from app.services.employee_settings_service import EmployeeSettingsService

router = Router(name="employee")


def _language_name(language_code: LanguageCode | None) -> str:
    mapping = {
        LanguageCode.UZ: "O'zbekcha",
        LanguageCode.RU: "Русский",
        LanguageCode.EN: "English",
    }
    return mapping.get(language_code or DEFAULT_LANGUAGE, "O'zbekcha")


def _rules_text(language) -> str:
    return "\n".join(
        [
            t(language, uz="Attendance qoidalari", ru="Правила attendance", en="Attendance rules"),
            t(language, uz="1. Joylashuvni yoqib, filial yaqinidan attendance qiling.", ru="1. Включите геолокацию и отмечайтесь рядом с филиалом.", en="1. Keep location enabled and attend near your branch."),
            t(language, uz="2. Joylashuv tekshiruvdan o'tgach dumaloq video yuboring.", ru="2. После проверки локации отправьте video note.", en="2. After location verification, send a video note."),
            t(language, uz="3. Ochiq session 10 daqiqada tugaydi.", ru="3. Открытая сессия истекает через 10 минут.", en="3. An open session expires after 10 minutes."),
            t(language, uz="4. Noto'g'ri urinishlar tizimda qayd etiladi.", ru="4. Некорректные попытки фиксируются системой.", en="4. Invalid attempts are recorded by the system."),
        ]
    )


def _format_employee_settings_overview(access: EmployeeAccessDTO) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    branch_name = access.employee.branch.name if access.employee.branch is not None else "-"
    department_name = access.employee.department.name if access.employee.department is not None else "-"
    shift_name = access.employee.shift.name if access.employee.shift is not None else "-"
    hire_date = access.employee.hire_date.isoformat() if access.employee.hire_date is not None else "-"
    return "\n".join(
        [
            t(language, uz="Sozlamalar bo'limi", ru="Раздел настроек", en="Settings section"),
            t(language, uz=f"🌐 Joriy til: {_language_name(access.user.language)}", ru=f"🌐 Текущий язык: {_language_name(access.user.language)}", en=f"🌐 Current language: {_language_name(access.user.language)}"),
            t(language, uz=f"📱 Kontakt telefon: {access.user.phone or '-'}", ru=f"📱 Контактный телефон: {access.user.phone or '-'}", en=f"📱 Contact phone: {access.user.phone or '-'}"),
            t(language, uz=f"🏢 Kompaniya: {access.company.name}", ru=f"🏢 Компания: {access.company.name}", en=f"🏢 Company: {access.company.name}"),
            t(language, uz=f"🏬 Filial: {branch_name}", ru=f"🏬 Филиал: {branch_name}", en=f"🏬 Branch: {branch_name}"),
            t(language, uz=f"🗂 Bo'lim: {department_name}", ru=f"🗂 Отдел: {department_name}", en=f"🗂 Department: {department_name}"),
            t(language, uz=f"⏰ Smena: {shift_name}", ru=f"⏰ Смена: {shift_name}", en=f"⏰ Shift: {shift_name}"),
            t(language, uz=f"🗓 Ishga kirgan sana: {hire_date}", ru=f"🗓 Дата приема: {hire_date}", en=f"🗓 Hire date: {hire_date}"),
            "",
            t(language, uz="Pastdagi tugmalar orqali til, kontakt telefon va shaxsiy ma'lumotlarni boshqaring.", ru="Управляйте языком, контактным телефоном и личной информацией через кнопки ниже.", en="Use the buttons below to manage language, contact phone, and personal information."),
        ]
    )


def _format_employee_profile(access: EmployeeAccessDTO) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    username = f"@{access.user.username}" if access.user.username else "-"
    return "\n".join(
        [
            t(language, uz="Profil ma'lumotlari", ru="Информация профиля", en="Profile information"),
            t(language, uz=f"👤 F.I.Sh: {access.user.full_name}", ru=f"👤 Ф.И.О.: {access.user.full_name}", en=f"👤 Full name: {access.user.full_name}"),
            t(language, uz=f"🆔 Telegram ID: {access.user.telegram_id}", ru=f"🆔 Telegram ID: {access.user.telegram_id}", en=f"🆔 Telegram ID: {access.user.telegram_id}"),
            t(language, uz=f"🔗 Username: {username}", ru=f"🔗 Username: {username}", en=f"🔗 Username: {username}"),
            t(language, uz=f"📱 Kontakt telefon: {access.user.phone or '-'}", ru=f"📱 Контактный телефон: {access.user.phone or '-'}", en=f"📱 Contact phone: {access.user.phone or '-'}"),
            t(language, uz=f"🌐 Til: {_language_name(access.user.language)}", ru=f"🌐 Язык: {_language_name(access.user.language)}", en=f"🌐 Language: {_language_name(access.user.language)}"),
        ]
    )


def _format_employee_work_info(access: EmployeeAccessDTO) -> str:
    language = access.user.language or DEFAULT_LANGUAGE
    branch_name = access.employee.branch.name if access.employee.branch is not None else "-"
    department_name = access.employee.department.name if access.employee.department is not None else "-"
    shift_name = access.employee.shift.name if access.employee.shift is not None else "-"
    position = access.employee.position or "-"
    employee_code = access.employee.employee_code or "-"
    hire_date = access.employee.hire_date.isoformat() if access.employee.hire_date is not None else "-"
    status_text = t(
        language,
        uz="Faol" if access.employee.is_active else "Nofaol",
        ru="Активен" if access.employee.is_active else "Неактивен",
        en="Active" if access.employee.is_active else "Inactive",
    )
    return "\n".join(
        [
            t(language, uz="Ish joyi ma'lumotlari", ru="Информация о работе", en="Work information"),
            t(language, uz=f"🏢 Kompaniya: {access.company.name}", ru=f"🏢 Компания: {access.company.name}", en=f"🏢 Company: {access.company.name}"),
            t(language, uz=f"🏬 Filial: {branch_name}", ru=f"🏬 Филиал: {branch_name}", en=f"🏬 Branch: {branch_name}"),
            t(language, uz=f"🗂 Bo'lim: {department_name}", ru=f"🗂 Отдел: {department_name}", en=f"🗂 Department: {department_name}"),
            t(language, uz=f"⏰ Smena: {shift_name}", ru=f"⏰ Смена: {shift_name}", en=f"⏰ Shift: {shift_name}"),
            t(language, uz=f"💼 Lavozim: {position}", ru=f"💼 Должность: {position}", en=f"💼 Position: {position}"),
            t(language, uz=f"🪪 Employee code: {employee_code}", ru=f"🪪 Employee code: {employee_code}", en=f"🪪 Employee code: {employee_code}"),
            t(language, uz=f"🗓 Ishga kirgan sana: {hire_date}", ru=f"🗓 Дата приема: {hire_date}", en=f"🗓 Hire date: {hire_date}"),
            t(language, uz=f"🔁 Holat: {status_text}", ru=f"🔁 Статус: {status_text}", en=f"🔁 Status: {status_text}"),
        ]
    )


async def _reload_employee_access(
    telegram_id: int,
    session: AsyncSession,
    settings: Settings,
) -> EmployeeAccessDTO:
    return await AuthService(session, settings).require_employee(telegram_id)


async def show_employee_settings_menu(
    message: Message,
    access: EmployeeAccessDTO,
) -> None:
    await message.answer(
        _format_employee_settings_overview(access),
        reply_markup=build_employee_settings_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


async def _edit_employee_settings_menu(
    message: Message,
    access: EmployeeAccessDTO,
) -> None:
    await message.edit_text(
        _format_employee_settings_overview(access),
        reply_markup=build_employee_settings_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.message(LocalizedTextFilter(*rules_button_texts()))
async def employee_rules_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await message.answer(_rules_text(access.user.language))


@router.message(LocalizedTextFilter(*settings_button_texts()))
async def employee_settings_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_employee_settings_menu(message, access)


@router.message(EmployeeSettingsStates.waiting_for_phone)
async def employee_settings_phone_input_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    settings_service = EmployeeSettingsService(session)
    try:
        phone = settings_service.parse_optional_phone(message.text or "")
    except InvalidPhoneError:
        await message.answer(
            t(
                access.user.language,
                uz="Telefon raqami noto'g'ri. Masalan: +998901234567 yoki `-` yuboring.",
                ru="Некорректный номер телефона. Например: +998901234567 или отправьте `-`.",
                en="Invalid phone number. Example: +998901234567 or send `-`.",
            ),
            reply_markup=build_employee_keyboard(access.user.language or DEFAULT_LANGUAGE),
        )
        return

    await settings_service.update_phone(
        access.user.telegram_id,
        phone,
        actor_telegram_id=access.user.telegram_id,
    )
    await state.clear()
    refreshed_access = await _reload_employee_access(access.user.telegram_id, session, settings)
    await message.answer(
        t(
            refreshed_access.user.language,
            uz="Kontakt telefon yangilandi.",
            ru="Контактный телефон обновлен.",
            en="Contact phone updated.",
        ),
        reply_markup=build_employee_keyboard(refreshed_access.user.language or DEFAULT_LANGUAGE),
    )
    await show_employee_settings_menu(message, refreshed_access)


@router.callback_query(F.data == "employee:settings:menu")
async def employee_settings_menu_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await _edit_employee_settings_menu(callback.message, access)


@router.callback_query(F.data == "employee:settings:language")
async def employee_settings_language_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
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
        reply_markup=build_employee_language_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data.startswith("employee:settings:language:set:"))
async def employee_settings_language_set_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
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
            reply_markup=build_employee_language_keyboard(
                access.user.language or DEFAULT_LANGUAGE,
                access.user.language or DEFAULT_LANGUAGE,
            ),
        )
        return

    settings_service = EmployeeSettingsService(session)
    await settings_service.update_language(
        access.user.telegram_id,
        target_language,
        actor_telegram_id=access.user.telegram_id,
    )
    refreshed_access = await _reload_employee_access(access.user.telegram_id, session, settings)

    await callback.answer(
        t(
            refreshed_access.user.language,
            uz="Til muvaffaqiyatli yangilandi.",
            ru="Язык успешно обновлен.",
            en="Language updated successfully.",
        )
    )
    await callback.message.edit_text(
        _format_employee_settings_overview(refreshed_access),
        reply_markup=build_employee_settings_keyboard(
            refreshed_access.user.language or DEFAULT_LANGUAGE,
        ),
    )
    await callback.message.answer(
        t(
            refreshed_access.user.language,
            uz="Panel va sozlamalar yangi tilga moslab yangilandi.",
            ru="Панель и настройки обновлены под новый язык.",
            en="The panel and settings were refreshed for the new language.",
        ),
        reply_markup=build_employee_keyboard(refreshed_access.user.language or DEFAULT_LANGUAGE),
    )


@router.callback_query(F.data == "employee:settings:phone")
async def employee_settings_phone_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await state.set_state(EmployeeSettingsStates.waiting_for_phone)
    await callback.answer()
    await callback.message.answer(
        t(
            access.user.language,
            uz="Yangi kontakt telefonni yuboring. O'chirish uchun `-` yuboring.",
            ru="Отправьте новый контактный телефон. Чтобы очистить, отправьте `-`.",
            en="Send the new contact phone. Send `-` to clear it.",
        ),
        reply_markup=build_employee_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.callback_query(F.data == "employee:settings:profile")
async def employee_settings_profile_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_employee_profile(access),
        reply_markup=build_employee_settings_navigation_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data == "employee:settings:work")
async def employee_settings_work_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_employee_work_info(access),
        reply_markup=build_employee_settings_navigation_keyboard(
            access.user.language or DEFAULT_LANGUAGE,
        ),
    )


@router.callback_query(F.data == "employee:settings:refresh")
async def employee_settings_refresh_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    refreshed_access = await _reload_employee_access(access.user.telegram_id, session, settings)
    await callback.answer(
        t(
            refreshed_access.user.language,
            uz="Sozlamalar yangilandi.",
            ru="Настройки обновлены.",
            en="Settings refreshed.",
        )
    )
    await _edit_employee_settings_menu(callback.message, refreshed_access)


@router.callback_query(F.data == "employee:settings:back")
async def employee_settings_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(
            access.user.language,
            uz="Employee paneliga qaytdingiz.",
            ru="Вы вернулись в employee панель.",
            en="You are back in the employee panel.",
        )
    )
    await show_employee_panel(callback.message, access, session)
