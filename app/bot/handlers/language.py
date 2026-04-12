from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.employee_common import show_employee_panel
from app.bot.handlers.public_onboarding import edit_public_onboarding_home
from app.bot.keyboards.reply.company_admin import build_company_admin_keyboard
from app.bot.keyboards.reply.super_admin import build_super_admin_keyboard
from app.core.config import Settings
from app.core.localization import t
from app.domain.dto.user_dto import StartFlowStatus, TelegramUserDTO
from app.domain.enums.language import LanguageCode
from app.services.auth_service import AuthService

router = Router(name="language")


@router.callback_query(F.data.startswith("lang:"))
async def language_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if callback.from_user is None or callback.data is None:
        return

    try:
        language = LanguageCode(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Unsupported language.", show_alert=True)
        return

    auth_service = AuthService(session, settings)
    telegram_user = TelegramUserDTO.from_aiogram(callback.from_user)
    result = await auth_service.handle_language_selection(telegram_user, language)

    await callback.answer(
        t(
            language,
            uz="Til saqlandi.",
            ru="Язык сохранен.",
            en="Language saved.",
        )
    )

    if callback.message is None:
        return

    if result.status is StartFlowStatus.SUPER_ADMIN:
        await callback.message.edit_text(
            t(
                language,
                uz="Til saqlandi. Super admin paneli tayyor.",
                ru="Язык сохранен. Панель супер-админа готова.",
                en="Language saved. The super admin panel is ready.",
            ),
            reply_markup=None,
        )
        await callback.message.answer(
            t(
                language,
                uz="Super admin paneli",
                ru="Панель супер-админа",
                en="Super admin panel",
            ),
            reply_markup=build_super_admin_keyboard(language),
        )
        return

    if result.status is StartFlowStatus.COMPANY_ADMIN:
        await callback.message.edit_text(
            t(
                language,
                uz="Til saqlandi. Company admin paneli tayyor.",
                ru="Язык сохранен. Панель company admin готова.",
                en="Language saved. The company admin panel is ready.",
            ),
            reply_markup=None,
        )
        await callback.message.answer(
            t(
                language,
                uz="Company admin paneli",
                ru="Панель company admin",
                en="Company admin panel",
            ),
            reply_markup=build_company_admin_keyboard(language),
        )
        return

    if result.status is StartFlowStatus.EMPLOYEE:
        employee_access = await auth_service.require_employee(callback.from_user.id)
        await callback.message.edit_text(
            t(
                language,
                uz="Til saqlandi. Employee paneli tayyor.",
                ru="Язык сохранен. Employee панель готова.",
                en="Language saved. The employee panel is ready.",
            ),
            reply_markup=None,
        )
        await show_employee_panel(callback.message, employee_access, session)
        return

    await callback.message.edit_text(
        t(
            language,
            uz="Til saqlandi. Public ariza oynasi tayyor.",
            ru="Язык сохранен. Публичная заявка готова.",
            en="Language saved. The public application view is ready.",
        ),
        reply_markup=None,
    )
    await edit_public_onboarding_home(callback.message, session, telegram_user, language)
