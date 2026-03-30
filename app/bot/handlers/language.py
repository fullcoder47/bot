from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

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

    await callback.message.edit_text(
        t(
            language,
            uz="Til saqlandi. Hozircha sizda kirish huquqi yo'q.",
            ru="Язык сохранен. Сейчас у вас нет доступа.",
            en="Language saved. You do not have access right now.",
        ),
        reply_markup=None,
    )
