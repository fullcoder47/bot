from __future__ import annotations

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply.company_admin import build_company_admin_keyboard
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import CompanyAdminAccessDTO
from app.domain.dto.employee_dto import CompanyAdminStatisticsDTO
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.services.auth_service import AuthService
from app.services.stats_service import StatsService


def format_company_admin_dashboard(
    language,
    company_name: str,
    stats: CompanyAdminStatisticsDTO,
) -> str:
    return "\n".join(
        [
            t(language, uz=f"Company admin dashboard: {company_name}", ru=f"Дашборд company admin: {company_name}", en=f"Company admin dashboard: {company_name}"),
            t(language, uz=f"👥 Jami ishchilar: {stats.total_employees}", ru=f"👥 Всего сотрудников: {stats.total_employees}", en=f"👥 Total employees: {stats.total_employees}"),
            t(language, uz=f"✅ Faol ishchilar: {stats.active_employees}", ru=f"✅ Активные сотрудники: {stats.active_employees}", en=f"✅ Active employees: {stats.active_employees}"),
            t(language, uz=f"⛔ Nofaol ishchilar: {stats.inactive_employees}", ru=f"⛔ Неактивные сотрудники: {stats.inactive_employees}", en=f"⛔ Inactive employees: {stats.inactive_employees}"),
            t(language, uz=f"🏢 Jami filiallar: {stats.total_branches}", ru=f"🏢 Всего филиалов: {stats.total_branches}", en=f"🏢 Total branches: {stats.total_branches}"),
            t(language, uz=f"🗂 Jami bo'limlar: {stats.total_departments}", ru=f"🗂 Всего отделов: {stats.total_departments}", en=f"🗂 Total departments: {stats.total_departments}"),
            t(language, uz=f"⏰ Jami smenalar: {stats.total_shifts}", ru=f"⏰ Всего смен: {stats.total_shifts}", en=f"⏰ Total shifts: {stats.total_shifts}"),
        ]
    )


async def require_company_admin_message(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> CompanyAdminAccessDTO | None:
    if message.from_user is None:
        return None

    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_company_admin(message.from_user.id)
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
                uz="Sizda company admin paneliga kirish huquqi yo'q.",
                ru="У вас нет доступа к панели company admin.",
                en="You do not have access to the company admin panel.",
            )
        )
    return None


async def require_company_admin_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> CompanyAdminAccessDTO | None:
    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_company_admin(callback.from_user.id)
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
                uz="Sizda company admin paneliga kirish huquqi yo'q.",
                ru="У вас нет доступа к панели company admin.",
                en="You do not have access to the company admin panel.",
            ),
            show_alert=True,
        )
    return None


async def show_company_admin_panel(message: Message, access: CompanyAdminAccessDTO, session: AsyncSession) -> None:
    stats = await StatsService(session).get_company_admin_statistics(access.company.id)
    await message.answer(
        format_company_admin_dashboard(access.user.language, access.company.name, stats),
        reply_markup=build_company_admin_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )
