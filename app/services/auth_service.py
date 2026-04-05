from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.company_dto import CompanyAdminAccessDTO
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.dto.user_dto import StartFlowResult, StartFlowStatus, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import AccessDeniedError
from app.services.company_admin_service import CompanyAdminService
from app.services.employee_service import EmployeeService
from app.services.localization_service import LocalizationService
from app.services.super_admin_service import SuperAdminService


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.user_repo = UserRepository(session)
        self.localization_service = LocalizationService(session)
        self.super_admin_service = SuperAdminService(session, settings)
        self.company_admin_service = CompanyAdminService(session)
        self.employee_service = EmployeeService(session)

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

        company_admin_access = await self._try_company_admin_access(
            telegram_user=telegram_user,
            language=user.language,
        )
        if company_admin_access is not None:
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.COMPANY_ADMIN,
                language=company_admin_access.user.language,
                user=company_admin_access.user,
            )

        employee_access = await self._try_employee_access(
            telegram_user=telegram_user,
            language=user.language,
        )
        if employee_access is not None:
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.EMPLOYEE,
                language=employee_access.user.language,
                user=employee_access.user,
            )

        await self.user_repo.update_role_and_status(
            user=user,
            role=UserRole.EMPLOYEE,
            is_active=False,
        )
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

        company_admin_access = await self._try_company_admin_access(
            telegram_user=telegram_user,
            language=language,
        )
        if company_admin_access is not None:
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.COMPANY_ADMIN,
                language=company_admin_access.user.language,
                user=company_admin_access.user,
            )

        employee_access = await self._try_employee_access(
            telegram_user=telegram_user,
            language=language,
        )
        if employee_access is not None:
            await self.session.commit()
            return StartFlowResult(
                status=StartFlowStatus.EMPLOYEE,
                language=employee_access.user.language,
                user=employee_access.user,
            )

        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
        if user is not None:
            await self.user_repo.update_role_and_status(
                user=user,
                role=UserRole.EMPLOYEE,
                is_active=False,
            )
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
        return await self.super_admin_service.require_access(telegram_id)

    async def require_company_admin(self, telegram_id: int) -> CompanyAdminAccessDTO:
        return await self.company_admin_service.require_company_admin(telegram_id)

    async def require_employee(self, telegram_id: int) -> EmployeeAccessDTO:
        return await self.employee_service.require_employee_access(telegram_id)

    async def _try_company_admin_access(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> CompanyAdminAccessDTO | None:
        try:
            return await self.company_admin_service.bootstrap_company_admin(
                telegram_user=telegram_user,
                language=language,
            )
        except AccessDeniedError:
            return None

    async def _try_employee_access(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> EmployeeAccessDTO | None:
        try:
            return await self.employee_service.bootstrap_employee_access(
                telegram_user=telegram_user,
                language=language,
            )
        except AccessDeniedError:
            return None
