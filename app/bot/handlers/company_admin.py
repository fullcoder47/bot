from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.role import RoleFilter
from app.bot.keyboards.reply.company_admin import (
    attendance_button_texts,
    settings_button_texts,
    workers_button_texts,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import CompanyAdminAccessDTO
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.enums.role import UserRole
from app.services.auth_service import AuthService

router = Router(name="company_admin")


async def _require_company_admin_access(
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


@router.message(RoleFilter(UserRole.COMPANY_ADMIN), F.text.in_(workers_button_texts()))
async def workers_placeholder_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await _require_company_admin_access(message, session, settings)
    if access is None:
        return

    await message.answer(
        t(
            access.user.language,
            uz="Ishchilar bo'limi keyingi bosqichda qo'shiladi.",
            ru="Раздел сотрудников будет добавлен на следующем этапе.",
            en="The employees section will be added in the next stage.",
        )
    )


@router.message(RoleFilter(UserRole.COMPANY_ADMIN), F.text.in_(attendance_button_texts()))
async def attendance_placeholder_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await _require_company_admin_access(message, session, settings)
    if access is None:
        return

    await message.answer(
        t(
            access.user.language,
            uz="Davomat bo'limi keyingi bosqichda qo'shiladi.",
            ru="Раздел посещаемости будет добавлен на следующем этапе.",
            en="The attendance section will be added in the next stage.",
        )
    )


@router.message(RoleFilter(UserRole.COMPANY_ADMIN), F.text.in_(settings_button_texts()))
async def company_admin_settings_placeholder_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await _require_company_admin_access(message, session, settings)
    if access is None:
        return

    await message.answer(
        t(
            access.user.language,
            uz="Sozlamalar bo'limi keyingi bosqichda kengaytiriladi.",
            ru="Раздел настроек будет расширен на следующем этапе.",
            en="The settings section will be expanded in the next stage.",
        )
    )
