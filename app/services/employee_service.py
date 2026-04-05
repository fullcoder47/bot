from __future__ import annotations

import re
from datetime import datetime
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.branch_repo import BranchRepository
from app.db.repositories.department_repo import DepartmentRepository
from app.db.repositories.employee_repo import EmployeeRepository
from app.db.repositories.shift_repo import ShiftRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.company_dto import CompanyDTO
from app.domain.dto.employee_dto import (
    EmployeeAccessDTO,
    EmployeeBranchLocationDTO,
    EmployeeCreateDTO,
    EmployeeDetailDTO,
    EmployeeFiltersDTO,
    EmployeeListPageDTO,
    EmployeeLocationValidationContextDTO,
    EmployeeUpdateDTO,
)
from app.domain.dto.user_dto import CreateUserDTO, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.exceptions.company_admin_exceptions import (
    BranchAssignmentRequiredError,
    BranchNotFoundError,
    EmployeeAlreadyExistsError,
    EmployeeNotFoundError,
    ForeignEntityScopeError,
    InvalidPhoneError,
)


class EmployeeService:
    DEFAULT_PAGE_SIZE = 5
    PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.branch_repo = BranchRepository(session)
        self.department_repo = DepartmentRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.user_repo = UserRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @classmethod
    def parse_phone(cls, value: str) -> str | None:
        normalized = cls.normalize_text(value)
        if not normalized or normalized == "-":
            return None
        if not cls.PHONE_PATTERN.fullmatch(normalized):
            raise InvalidPhoneError()
        return normalized

    @staticmethod
    def parse_optional_telegram_id(value: str) -> int | None:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if not normalized.isdigit():
            raise ValueError("telegram_id")
        telegram_id = int(normalized)
        if telegram_id <= 0:
            raise ValueError("telegram_id")
        return telegram_id

    @staticmethod
    def parse_optional_date(value: str):
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        return datetime.strptime(normalized, "%Y-%m-%d").date()

    @staticmethod
    def normalize_search_query(query: str) -> str:
        return " ".join(query.split()).strip()

    async def bootstrap_employee_access(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> EmployeeAccessDTO:
        employee = await self.employee_repo.get_by_telegram_id(telegram_user.telegram_id)
        if employee is None or employee.company is None or not employee.is_active or not employee.company.is_active:
            raise AccessDeniedError(language)

        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)
        if user is None:
            user = await self.user_repo.create(
                CreateUserDTO(
                    telegram_id=telegram_user.telegram_id,
                    full_name=telegram_user.full_name,
                    username=telegram_user.username,
                    phone=telegram_user.phone,
                    role=UserRole.EMPLOYEE,
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
                    role=UserRole.EMPLOYEE,
                    is_active=True,
                )

        if employee.user_id != user.id:
            await self.employee_repo.link_user(employee, user.id)

        return self._build_employee_access(user, employee)

    async def require_employee_access(self, telegram_id: int) -> EmployeeAccessDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None or user.language is None:
            raise LanguageSelectionRequiredError()

        employee = await self.employee_repo.get_by_telegram_id(telegram_id)
        if employee is None or employee.company is None:
            raise AccessDeniedError(user.language)

        if not employee.is_active or not employee.company.is_active:
            raise AccessDeniedError(user.language)

        if user.role is not UserRole.EMPLOYEE or not user.is_active:
            raise AccessDeniedError(user.language)

        if employee.user_id != user.id:
            await self.employee_repo.link_user(employee, user.id)

        return self._build_employee_access(user, employee)

    async def create_employee(
        self,
        company_id: int,
        payload: EmployeeCreateDTO,
        actor_telegram_id: int | None = None,
    ) -> EmployeeDetailDTO:
        normalized_full_name = self.normalize_text(payload.full_name)
        if not normalized_full_name:
            raise EmployeeAlreadyExistsError("")
        await self._validate_payload(company_id, payload)

        employee = await self.employee_repo.create(
            company_id,
            EmployeeCreateDTO(
                full_name=normalized_full_name,
                phone=payload.phone,
                telegram_id=payload.telegram_id,
                employee_code=self.normalize_text(payload.employee_code or "") or None,
                position=self.normalize_text(payload.position or "") or None,
                branch_id=payload.branch_id,
                department_id=payload.department_id,
                shift_id=payload.shift_id,
                hire_date=payload.hire_date,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="employee_created",
            entity_type="employee",
            entity_id=employee.id,
            metadata_json={"company_id": company_id, "full_name": employee.full_name},
        )
        await self.session.commit()
        return await self.get_employee_detail(company_id, employee.id)

    async def update_employee(
        self,
        company_id: int,
        employee_id: int,
        payload: EmployeeUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> EmployeeDetailDTO:
        employee = await self._get_employee_or_raise(company_id, employee_id)
        normalized_full_name = self.normalize_text(payload.full_name)
        if not normalized_full_name:
            raise EmployeeAlreadyExistsError("")
        create_payload = EmployeeCreateDTO(
            full_name=normalized_full_name,
            phone=payload.phone,
            telegram_id=payload.telegram_id,
            employee_code=payload.employee_code,
            position=payload.position,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            shift_id=payload.shift_id,
            hire_date=payload.hire_date,
            is_active=payload.is_active,
        )
        await self._validate_payload(company_id, create_payload, exclude_employee_id=employee.id)

        await self.employee_repo.update(
            employee,
            EmployeeUpdateDTO(
                full_name=normalized_full_name,
                phone=payload.phone,
                telegram_id=payload.telegram_id,
                employee_code=self.normalize_text(payload.employee_code or "") or None,
                position=self.normalize_text(payload.position or "") or None,
                branch_id=payload.branch_id,
                department_id=payload.department_id,
                shift_id=payload.shift_id,
                hire_date=payload.hire_date,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="employee_updated",
            entity_type="employee",
            entity_id=employee.id,
            metadata_json={"company_id": company_id, "full_name": employee.full_name},
        )
        await self.session.commit()
        return await self.get_employee_detail(company_id, employee.id)

    async def toggle_employee_status(
        self,
        company_id: int,
        employee_id: int,
        actor_telegram_id: int | None = None,
    ) -> EmployeeDetailDTO:
        employee = await self._get_employee_or_raise(company_id, employee_id)
        await self.employee_repo.toggle_is_active(employee)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="employee_status_toggled",
            entity_type="employee",
            entity_id=employee.id,
            metadata_json={"company_id": company_id, "is_active": employee.is_active},
        )
        await self.session.commit()
        return await self.get_employee_detail(company_id, employee.id)

    async def get_employee_detail(self, company_id: int, employee_id: int) -> EmployeeDetailDTO:
        employee = await self._get_employee_or_raise(company_id, employee_id)
        return EmployeeDetailDTO.from_model(employee)

    async def list_employees(
        self,
        company_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: EmployeeFiltersDTO | None = None,
    ) -> EmployeeListPageDTO:
        safe_page_size = max(1, page_size)
        employees, total_items = await self.employee_repo.list_paginated(company_id, page, safe_page_size, filters)
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            employees, total_items = await self.employee_repo.list_paginated(
                company_id,
                normalized_page,
                safe_page_size,
                filters,
            )
        return EmployeeListPageDTO(
            items=[EmployeeDetailDTO.from_model(employee) for employee in employees],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def get_employee_branch_location(
        self,
        company_id: int,
        employee_id: int,
    ) -> EmployeeBranchLocationDTO | None:
        employee = await self.get_employee_detail(company_id, employee_id)
        if employee.branch is None:
            return None
        return EmployeeBranchLocationDTO(
            branch_id=employee.branch.id,
            branch_name=employee.branch.name,
            latitude=employee.branch.latitude,
            longitude=employee.branch.longitude,
            allowed_radius_meters=employee.branch.allowed_radius_meters,
            is_location_strict=employee.branch.is_location_strict,
        )

    async def branch_has_valid_location(self, company_id: int, employee_id: int) -> bool:
        branch_location = await self.get_employee_branch_location(company_id, employee_id)
        if branch_location is None:
            return False
        return (
            branch_location.latitude is not None
            and branch_location.longitude is not None
            and branch_location.allowed_radius_meters is not None
        )

    async def prepare_location_validation_context(
        self,
        company_id: int,
        employee_id: int,
    ) -> EmployeeLocationValidationContextDTO:
        employee = await self.get_employee_detail(company_id, employee_id)
        branch_location = await self.get_employee_branch_location(company_id, employee_id)
        return EmployeeLocationValidationContextDTO(
            employee=employee,
            branch_location=branch_location,
            has_valid_location=branch_location is not None
            and branch_location.latitude is not None
            and branch_location.longitude is not None
            and branch_location.allowed_radius_meters is not None,
        )

    async def _validate_payload(
        self,
        company_id: int,
        payload: EmployeeCreateDTO,
        *,
        exclude_employee_id: int | None = None,
    ) -> None:
        if payload.branch_id is None:
            raise BranchAssignmentRequiredError()

        branch = await self.branch_repo.get_by_id(company_id, payload.branch_id)
        if branch is None:
            raise BranchNotFoundError(payload.branch_id)

        if payload.department_id is not None:
            department = await self.department_repo.get_by_id(company_id, payload.department_id)
            if department is None:
                raise ForeignEntityScopeError()

        if payload.shift_id is not None:
            shift = await self.shift_repo.get_by_id(company_id, payload.shift_id)
            if shift is None:
                raise ForeignEntityScopeError()

        employee_code = self.normalize_text(payload.employee_code or "")
        if employee_code:
            existing_employee = await self.employee_repo.get_by_employee_code(company_id, employee_code)
            if existing_employee is not None and existing_employee.id != exclude_employee_id:
                raise EmployeeAlreadyExistsError(employee_code)

    async def _get_employee_or_raise(self, company_id: int, employee_id: int):
        employee = await self.employee_repo.get_by_id(company_id, employee_id)
        if employee is None:
            raise EmployeeNotFoundError(employee_id)
        return employee

    @staticmethod
    def _build_employee_access(user, employee) -> EmployeeAccessDTO:
        return EmployeeAccessDTO(
            user=UserDTO.from_model(user),
            company=CompanyDTO.from_model(employee.company),
            employee=EmployeeDetailDTO.from_model(employee),
        )
