from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.company_dto import CompanyStatisticsDTO
from app.domain.dto.user_dto import CreateUserDTO, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import (
    LanguageSelectionRequiredError,
    UnauthorizedAccessError,
)


class SuperAdminService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)
        self.company_admin_invite_repo = CompanyAdminInviteRepository(session)

    def is_super_admin_allowed(self, telegram_id: int) -> bool:
        return telegram_id in self.settings.super_admin_id_set

    async def bootstrap_super_admin(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> UserDTO:
        if not self.is_super_admin_allowed(telegram_user.telegram_id):
            raise UnauthorizedAccessError(language)

        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)

        if user is None:
            user = await self.user_repo.create(
                CreateUserDTO(
                    telegram_id=telegram_user.telegram_id,
                    full_name=telegram_user.full_name,
                    username=telegram_user.username,
                    phone=telegram_user.phone,
                    role=UserRole.SUPER_ADMIN,
                    language=language,
                    is_active=True,
                )
            )
        else:
            await self.user_repo.update_profile_fields(user, telegram_user)
            if user.language != language:
                await self.user_repo.update_language(user, language)
            await self.user_repo.promote_to_super_admin_if_allowed(
                user=user,
                allowed_ids=self.settings.super_admin_id_set,
            )
            user.is_active = True
            user.role = UserRole.SUPER_ADMIN
            await self.session.flush()

        return UserDTO.from_model(user)

    async def require_access(self, telegram_id: int) -> UserDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None or user.language is None:
            raise LanguageSelectionRequiredError()

        if not self.is_super_admin_allowed(telegram_id):
            raise UnauthorizedAccessError(user.language)

        if user.role is not UserRole.SUPER_ADMIN or not user.is_active:
            raise UnauthorizedAccessError(user.language)

        return UserDTO.from_model(user)

    async def get_statistics(self) -> CompanyStatisticsDTO:
        total_companies = await self.company_repo.count_all()
        active_companies = await self.company_repo.count_by_status(True)
        inactive_companies = await self.company_repo.count_by_status(False)
        companies_with_admin = await self.company_admin_invite_repo.count_active_assignments()

        return CompanyStatisticsDTO(
            total_companies=total_companies,
            active_companies=active_companies,
            inactive_companies=inactive_companies,
            companies_with_admin=companies_with_admin,
        )
