from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.company_dto import (
    CompanyAdminAccessDTO,
    CompanyAdminAssignDTO,
    CompanyDTO,
    CompanyDetailDTO,
)
from app.domain.dto.user_dto import CreateUserDTO, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.exceptions.company_exceptions import CompanyNotFoundError, InvalidTelegramIdError


class CompanyAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)
        self.company_admin_invite_repo = CompanyAdminInviteRepository(session)

    async def assign_company_admin(self, payload: CompanyAdminAssignDTO) -> CompanyDetailDTO:
        if payload.telegram_id <= 0:
            raise InvalidTelegramIdError()

        company = await self.company_repo.get_by_id(payload.company_id)
        if company is None:
            raise CompanyNotFoundError(payload.company_id)

        invite = await self.company_admin_invite_repo.upsert(payload)

        user = await self.user_repo.get_by_telegram_id(payload.telegram_id)
        if user is not None and user.role is not UserRole.SUPER_ADMIN:
            await self.user_repo.update_role_and_status(
                user=user,
                role=UserRole.COMPANY_ADMIN,
                is_active=True,
            )

        await self.session.commit()
        return CompanyDetailDTO.from_model(company, invite)

    async def bootstrap_company_admin(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> CompanyAdminAccessDTO:
        invite = await self.company_admin_invite_repo.get_active_by_telegram_id(telegram_user.telegram_id)
        if invite is None or invite.company is None:
            raise AccessDeniedError(language)

        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
        if user is None:
            user = await self.user_repo.create(
                CreateUserDTO(
                    telegram_id=telegram_user.telegram_id,
                    full_name=telegram_user.full_name,
                    username=telegram_user.username,
                    phone=telegram_user.phone,
                    role=UserRole.COMPANY_ADMIN,
                    language=language,
                    is_active=True,
                )
            )
        else:
            await self.user_repo.update_profile_fields(user, telegram_user)
            if user.language != language:
                await self.user_repo.update_language(user, language)
            if user.role is not UserRole.SUPER_ADMIN:
                await self.user_repo.update_role_and_status(
                    user=user,
                    role=UserRole.COMPANY_ADMIN,
                    is_active=True,
                )

        return CompanyAdminAccessDTO(
            user=UserDTO.from_model(user),
            company=CompanyDTO.from_model(invite.company),
        )

    async def require_company_admin(self, telegram_id: int) -> CompanyAdminAccessDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None or user.language is None:
            raise LanguageSelectionRequiredError()

        invite = await self.company_admin_invite_repo.get_active_by_telegram_id(telegram_id)
        if invite is None or invite.company is None:
            raise AccessDeniedError(user.language)

        if user.role is not UserRole.COMPANY_ADMIN or not user.is_active:
            raise AccessDeniedError(user.language)

        return CompanyAdminAccessDTO(
            user=UserDTO.from_model(user),
            company=CompanyDTO.from_model(invite.company),
        )
