from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.keyboards.inline.super_admin import build_super_admin_settings_keyboard
from app.bot.keyboards.reply.company_admin import build_company_admin_keyboard
from app.bot.keyboards.reply.super_admin import (
    build_super_admin_keyboard,
    settings_button_texts,
    statistics_button_texts,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import CompanyStatisticsDTO
from app.domain.dto.user_dto import UserDTO
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.services.auth_service import AuthService
from app.services.super_admin_service import SuperAdminService

router = Router(name="super_admin")


def _format_statistics(language, stats: CompanyStatisticsDTO) -> str:
    return "\n".join(
        [
            t(language, uz="📊 Statistika", ru="📊 Статистика", en="📊 Statistics"),
            t(
                language,
                uz=f"🏢 Jami kompaniyalar: {stats.total_companies}",
                ru=f"🏢 Всего компаний: {stats.total_companies}",
                en=f"🏢 Total companies: {stats.total_companies}",
            ),
            t(
                language,
                uz=f"✅ Faol kompaniyalar: {stats.active_companies}",
                ru=f"✅ Активные компании: {stats.active_companies}",
                en=f"✅ Active companies: {stats.active_companies}",
            ),
            t(
                language,
                uz=f"⛔ Nofaol kompaniyalar: {stats.inactive_companies}",
                ru=f"⛔ Неактивные компании: {stats.inactive_companies}",
                en=f"⛔ Inactive companies: {stats.inactive_companies}",
            ),
            t(
                language,
                uz=f"👤 Admin biriktirilgan kompaniyalar: {stats.companies_with_admin}",
                ru=f"👤 Компании с назначенным админом: {stats.companies_with_admin}",
                en=f"👤 Companies with assigned admin: {stats.companies_with_admin}",
            ),
        ]
    )


async def _require_super_admin_user(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> UserDTO | None:
    if message.from_user is None:
        return None

    auth_service = AuthService(session, settings)

    try:
        return await auth_service.require_super_admin(message.from_user.id)
    except LanguageSelectionRequiredError:
        await message.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Avval /start buyrug'ini yuboring.",
                ru="Сначала отправьте команду /start.",
                en="Please send /start first.",
            )
        )
    except AccessDeniedError as exc:
        await message.answer(
            t(
                exc.language or DEFAULT_LANGUAGE,
                uz="Sizda bu bo'limga kirish huquqi yo'q.",
                ru="У вас нет доступа к этому разделу.",
                en="You do not have access to this section.",
            )
        )

    return None


async def _require_super_admin_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> UserDTO | None:
    auth_service = AuthService(session, settings)

    try:
        return await auth_service.require_super_admin(callback.from_user.id)
    except LanguageSelectionRequiredError:
        await callback.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Avval /start buyrug'ini yuboring.",
                ru="Сначала отправьте команду /start.",
                en="Please send /start first.",
            ),
            show_alert=True,
        )
    except AccessDeniedError as exc:
        await callback.answer(
            t(
                exc.language or DEFAULT_LANGUAGE,
                uz="Sizda bu bo'limga kirish huquqi yo'q.",
                ru="У вас нет доступа к этому разделу.",
                en="You do not have access to this section.",
            ),
            show_alert=True,
        )

    return None


async def _show_super_admin_panel(message: Message, language) -> None:
    await message.answer(
        t(
            language,
            uz="Super admin paneli",
            ru="Панель супер-админа",
            en="Super admin panel",
        ),
        reply_markup=build_super_admin_keyboard(language or DEFAULT_LANGUAGE),
    )


@router.message(Command("panel"))
async def super_admin_panel_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if message.from_user is None:
        return

    await state.clear()
    auth_service = AuthService(session, settings)

    try:
        user = await auth_service.require_super_admin(message.from_user.id)
    except LanguageSelectionRequiredError:
        await message.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Avval /start buyrug'ini yuboring.",
                ru="Сначала отправьте команду /start.",
                en="Please send /start first.",
            )
        )
        return
    except AccessDeniedError:
        try:
            company_access = await auth_service.require_company_admin(message.from_user.id)
        except LanguageSelectionRequiredError:
            await message.answer(
                t(
                    DEFAULT_LANGUAGE,
                    uz="Avval /start buyrug'ini yuboring.",
                    ru="Сначала отправьте команду /start.",
                    en="Please send /start first.",
                )
            )
            return
        except AccessDeniedError as exc:
            await message.answer(
                t(
                    exc.language or DEFAULT_LANGUAGE,
                    uz="Sizda panelga kirish huquqi yo'q.",
                    ru="У вас нет доступа к панели.",
                    en="You do not have access to the panel.",
                )
            )
            return

        await message.answer(
            t(
                company_access.user.language,
                uz=f"Company admin paneli: {company_access.company.name}",
                ru=f"Панель company admin: {company_access.company.name}",
                en=f"Company admin panel: {company_access.company.name}",
            ),
            reply_markup=build_company_admin_keyboard(company_access.user.language or DEFAULT_LANGUAGE),
        )
        return

    await _show_super_admin_panel(message, user.language or DEFAULT_LANGUAGE)


@router.message(StateFilter(None), LocalizedTextFilter(*statistics_button_texts()))
async def statistics_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_user(message, session, settings)
    if user is None:
        return

    super_admin_service = SuperAdminService(session, settings)
    statistics = await super_admin_service.get_statistics()
    await message.answer(_format_statistics(user.language, statistics))


@router.message(StateFilter(None), LocalizedTextFilter(*settings_button_texts()))
async def settings_menu_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_user(message, session, settings)
    if user is None:
        return

    await message.answer(
        t(
            user.language,
            uz="Sozlamalar bo'limi",
            ru="Раздел настроек",
            en="Settings section",
        ),
        reply_markup=build_super_admin_settings_keyboard(user.language),
    )


@router.callback_query(F.data == "superadmin:settings:language")
async def settings_language_placeholder_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return

    await callback.answer()
    await callback.message.edit_text(
        t(
            user.language,
            uz="Tilni o'zgartirish keyingi bosqichda qo'shiladi.",
            ru="Смена языка будет добавлена на следующем этапе.",
            en="Change language will be added in the next stage.",
        ),
        reply_markup=build_super_admin_settings_keyboard(user.language),
    )


@router.callback_query(F.data == "superadmin:settings:system")
async def settings_system_placeholder_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return

    await callback.answer()
    await callback.message.edit_text(
        t(
            user.language,
            uz="Tizim sozlamalari keyingi bosqichda kengaytiriladi.",
            ru="Системные настройки будут расширены на следующем этапе.",
            en="System settings will be expanded in the next stage.",
        ),
        reply_markup=build_super_admin_settings_keyboard(user.language),
    )


@router.callback_query(F.data == "superadmin:settings:back")
async def settings_back_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return

    await callback.answer()
    await callback.message.edit_text(
        t(
            user.language,
            uz="Super admin paneliga qaytdingiz.",
            ru="Вы вернулись в панель супер-админа.",
            en="You are back in the super admin panel.",
        )
    )
    await _show_super_admin_panel(callback.message, user.language or DEFAULT_LANGUAGE)
