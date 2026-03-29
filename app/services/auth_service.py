from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.user_dto import StartFlowResult, StartFlowStatus, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.services.localization_service import LocalizationService
from app.services.super_admin_service import SuperAdminService


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.user_repo = UserRepository(session)
        self.localization_service = LocalizationService(session)
        self.super_admin_service = SuperAdminService(session, settings)

    async def start(self, telegram_user: TelegramUserDTO) -> StartFlowResult:
        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)

        if user is None or user.language is None:
            return StartFlowResult(status=StartFlowStatus.REQUEST_LANGUAGE)

        await self.user_repo.update_profile_fields(user, telegram_user)

        if self.super_admin_service.is_super_admin_allowed(telegram_user.telegram_id):
            admin_user = await self.super_admin_service.bootstrap_super_admin(
                telegram_user=telegram_user,
                language=user.language,
            )
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.SUPER_ADMIN,
                language=admin_user.language,
                user=admin_user,
            )

        user.is_active = False
        await self.session.commit()
        return StartFlowResult(
            status=StartFlowStatus.ACCESS_DENIED,
            language=user.language,
            user=UserDTO.from_model(user),
        )

    async def handle_language_selection(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> StartFlowResult:
        saved_user = await self.localization_service.save_language_selection(telegram_user, language)

        if self.super_admin_service.is_super_admin_allowed(telegram_user.telegram_id):
            admin_user = await self.super_admin_service.bootstrap_super_admin(
                telegram_user=telegram_user,
                language=language,
            )
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.SUPER_ADMIN,
                language=admin_user.language,
                user=admin_user,
            )

        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
        if user is not None:
            user.is_active = False
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.ACCESS_DENIED,
                language=user.language,
                user=UserDTO.from_model(user),
            )

        return StartFlowResult(
            status=StartFlowStatus.ACCESS_DENIED,
            language=saved_user.language,
            user=saved_user,
        )

    async def require_super_admin(self, telegram_id: int) -> UserDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None or user.language is None:
            raise LanguageSelectionRequiredError()

        if not self.super_admin_service.is_super_admin_allowed(telegram_id):
            raise AccessDeniedError(user.language)

        if user.role is not UserRole.SUPER_ADMIN or not user.is_active:
            raise AccessDeniedError(user.language)

        return UserDTO.from_model(user)
