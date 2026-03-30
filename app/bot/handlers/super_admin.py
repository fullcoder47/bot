from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.keyboards.reply.company_admin import build_company_admin_keyboard
from app.bot.keyboards.reply.super_admin import (
    build_super_admin_keyboard,
    settings_button_texts,
    statistics_button_texts,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.user_dto import UserDTO
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.services.auth_service import AuthService

router = Router(name="super_admin")


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


@router.message(Command("panel"))
async def super_admin_panel_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if message.from_user is None:
        return

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

    await message.answer(
        t(
            user.language,
            uz="Super admin paneli",
            ru="Панель супер-админа",
            en="Super admin panel",
        ),
        reply_markup=build_super_admin_keyboard(user.language or DEFAULT_LANGUAGE),
    )


@router.message(LocalizedTextFilter(*statistics_button_texts()))
async def statistics_placeholder_handler(
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
            uz="Statistika bo'limi tez orada qo'shiladi.",
            ru="Раздел статистики скоро будет добавлен.",
            en="The statistics section will be added soon.",
        )
    )


@router.message(LocalizedTextFilter(*settings_button_texts()))
async def settings_placeholder_handler(
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
            uz="Sozlamalar bo'limi tez orada qo'shiladi. Tilni o'zgartirish keyingi bosqichda qo'shiladi.",
            ru="Раздел настроек скоро будет добавлен. Смена языка появится на следующем этапе.",
            en="The settings section will be added soon. Change language will be added in the next stage.",
        )
    )
