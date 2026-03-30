from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
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
from app.domain.exceptions.company_exceptions import (
    CompanyAdminAssignmentError,
    CompanyNotFoundError,
    InvalidTelegramIdError,
)


class CompanyAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    async def assign_company_admin(
        self,
        payload: CompanyAdminAssignDTO,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        if payload.telegram_id <= 0:
            raise InvalidTelegramIdError()

        company = await self.company_repo.get_by_id(payload.company_id)
        if company is None:
            raise CompanyNotFoundError(payload.company_id)

        existing_assignment = await self.company_admin_repo.get_by_company_id(payload.company_id)
        previous_telegram_id = existing_assignment.telegram_id if existing_assignment else None
        invite = await self.company_admin_repo.upsert_assignment(payload)

        user = await self.user_repo.get_by_telegram_id(payload.telegram_id)
        if user is not None and user.role is not UserRole.SUPER_ADMIN:
            await self.user_repo.update_role_and_status(
                user=user,
                role=UserRole.COMPANY_ADMIN,
                is_active=True,
            )

        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_admin_assigned" if previous_telegram_id is None else "company_admin_reassigned",
            entity_type="company",
            entity_id=company.id,
            metadata_json={
                "previous_telegram_id": previous_telegram_id,
                "telegram_id": invite.telegram_id,
                "is_active": invite.is_active,
            },
        )
        await self.session.commit()
        return CompanyDetailDTO.from_model(company, invite)

    async def deactivate_company_admin(
        self,
        company_id: int,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)

        invite = await self.company_admin_repo.get_active_by_company_id(company_id)
        if invite is None:
            raise CompanyAdminAssignmentError("Active company admin assignment was not found.")

        deactivated_invite = await self.company_admin_repo.deactivate_by_company_id(company_id)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_admin_deactivated",
            entity_type="company",
            entity_id=company.id,
            metadata_json={"telegram_id": invite.telegram_id},
        )
        await self.session.commit()
        return CompanyDetailDTO.from_model(company, deactivated_invite)

    async def remove_company_admin(
        self,
        company_id: int,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)

        invite = await self.company_admin_repo.get_by_company_id(company_id)
        if invite is None:
            raise CompanyAdminAssignmentError("Company admin assignment was not found.")

        telegram_id = invite.telegram_id
        await self.company_admin_repo.remove_assignment(company_id)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_admin_removed",
            entity_type="company",
            entity_id=company.id,
            metadata_json={"telegram_id": telegram_id},
        )
        await self.session.commit()
        return CompanyDetailDTO.from_model(company)

    async def bootstrap_company_admin(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> CompanyAdminAccessDTO:
        invite = await self.company_admin_repo.get_active_by_telegram_id(telegram_user.telegram_id)
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

        invite = await self.company_admin_repo.get_active_by_telegram_id(telegram_id)
        if invite is None or invite.company is None:
            raise AccessDeniedError(user.language)

        if user.role is not UserRole.COMPANY_ADMIN or not user.is_active:
            raise AccessDeniedError(user.language)

        return CompanyAdminAccessDTO(
            user=UserDTO.from_model(user),
            company=CompanyDTO.from_model(invite.company),
        )
