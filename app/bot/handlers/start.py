from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline.language import build_language_keyboard
from app.bot.keyboards.reply.company_admin import build_company_admin_keyboard
from app.bot.keyboards.reply.super_admin import build_super_admin_keyboard
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import SuperAdminDashboardDTO
from app.domain.dto.user_dto import StartFlowStatus, TelegramUserDTO
from app.services.auth_service import AuthService
from app.services.stats_service import StatsService

router = Router(name="start")
logger = logging.getLogger(__name__)


def _format_super_admin_dashboard(language, dashboard: SuperAdminDashboardDTO) -> str:
    recent_lines = [
        t(language, uz="So'nggi 5 kompaniya:", ru="Последние 5 компаний:", en="Latest 5 companies:")
    ]
    if dashboard.recent_companies:
        recent_lines.extend(
            f"• {company.name} ({company.plan.value})"
            for company in dashboard.recent_companies
        )
    else:
        recent_lines.append(
            t(
                language,
                uz="Hozircha kompaniyalar mavjud emas.",
                ru="Пока компаний нет.",
                en="There are no companies yet.",
            )
        )

    return "\n".join(
        [
            t(language, uz="Super admin dashboard", ru="Дашборд супер-админа", en="Super admin dashboard"),
            t(
                language,
                uz=f"🏢 Jami kompaniyalar: {dashboard.total_companies}",
                ru=f"🏢 Всего компаний: {dashboard.total_companies}",
                en=f"🏢 Total companies: {dashboard.total_companies}",
            ),
            t(
                language,
                uz=f"✅ Faol kompaniyalar: {dashboard.active_companies}",
                ru=f"✅ Активные компании: {dashboard.active_companies}",
                en=f"✅ Active companies: {dashboard.active_companies}",
            ),
            t(
                language,
                uz=f"⛔ Nofaol kompaniyalar: {dashboard.inactive_companies}",
                ru=f"⛔ Неактивные компании: {dashboard.inactive_companies}",
                en=f"⛔ Inactive companies: {dashboard.inactive_companies}",
            ),
            t(
                language,
                uz=f"⌛ Muddati tugagan subscriptionlar: {dashboard.expired_companies}",
                ru=f"⌛ Истекшие подписки: {dashboard.expired_companies}",
                en=f"⌛ Expired subscriptions: {dashboard.expired_companies}",
            ),
            t(
                language,
                uz=f"👤 Admin biriktirilgan kompaniyalar: {dashboard.companies_with_admin}",
                ru=f"👤 Компании с админом: {dashboard.companies_with_admin}",
                en=f"👤 Companies with admin: {dashboard.companies_with_admin}",
            ),
            t(
                language,
                uz=f"📭 Admin biriktirilmagan kompaniyalar: {dashboard.companies_without_admin}",
                ru=f"📭 Компании без админа: {dashboard.companies_without_admin}",
                en=f"📭 Companies without admin: {dashboard.companies_without_admin}",
            ),
            t(language, uz="📦 Tariflar taqsimoti:", ru="📦 Распределение тарифов:", en="📦 Plan distribution:"),
            f"FREE: {dashboard.plan_distribution.free}",
            f"BASIC: {dashboard.plan_distribution.basic}",
            f"PRO: {dashboard.plan_distribution.pro}",
            "",
            *recent_lines,
        ]
    )


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

    if result.status is StartFlowStatus.COMPANY_ADMIN:
        await message.answer(
            t(
                language,
                uz="Company admin paneliga xush kelibsiz.",
                ru="Добро пожаловать в панель company admin.",
                en="Welcome to the company admin panel.",
            ),
            reply_markup=build_company_admin_keyboard(language),
        )
        return

    dashboard = await StatsService(session).get_super_admin_dashboard()
    await message.answer(
        t(
            language,
            uz="Super admin paneliga xush kelibsiz.",
            ru="Добро пожаловать в панель супер-админа.",
            en="Welcome to the super admin panel.",
        )
    )
    await message.answer(
        _format_super_admin_dashboard(language, dashboard),
        reply_markup=build_super_admin_keyboard(language),
    )
