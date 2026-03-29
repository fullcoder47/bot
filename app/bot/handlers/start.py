from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline.language import build_language_keyboard
from app.bot.keyboards.reply.super_admin import build_super_admin_keyboard
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.user_dto import StartFlowStatus, TelegramUserDTO
from app.services.auth_service import AuthService

router = Router(name="start")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if message.from_user is None:
        logger.warning("Received /start update without from_user.")
        return

    auth_service = AuthService(session, settings)
    telegram_user = TelegramUserDTO.from_aiogram(message.from_user)
    result = await auth_service.start(telegram_user)

    if result.status is StartFlowStatus.REQUEST_LANGUAGE:
        await message.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Iltimos, tilni tanlang.",
                ru="Пожалуйста, выберите язык.",
                en="Please choose a language.",
            ),
            reply_markup=build_language_keyboard(),
        )
        return

    language = result.language or DEFAULT_LANGUAGE

    if result.status is StartFlowStatus.ACCESS_DENIED:
        await message.answer(
            t(
                language,
                uz="Sizda bu botdan foydalanish huquqi yo'q.",
                ru="У вас нет доступа к этому боту.",
                en="You do not have access to this bot.",
            )
        )
        return

    await message.answer(
        t(
            language,
            uz="Super admin paneliga xush kelibsiz.",
            ru="Добро пожаловать в панель супер-админа.",
            en="Welcome to the super admin panel.",
        ),
        reply_markup=build_super_admin_keyboard(language),
    )
