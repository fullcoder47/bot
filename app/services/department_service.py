from __future__ import annotations

from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.department_repo import DepartmentRepository
from app.db.repositories.employee_repo import EmployeeRepository
from app.domain.dto.department_dto import (
    DepartmentCreateDTO,
    DepartmentDTO,
    DepartmentListPageDTO,
    DepartmentUpdateDTO,
)
from app.domain.exceptions.company_admin_exceptions import (
    DepartmentAlreadyExistsError,
    DepartmentDeleteRestrictedError,
    DepartmentNotFoundError,
)


class DepartmentService:
    DEFAULT_PAGE_SIZE = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.department_repo = DepartmentRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.split()).strip()

    async def create_department(
        self,
        company_id: int,
        payload: DepartmentCreateDTO,
        actor_telegram_id: int | None = None,
    ) -> DepartmentDTO:
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise DepartmentAlreadyExistsError("")

        await self.ensure_name_available(company_id, normalized_name)
        department = await self.department_repo.create(
            company_id,
            DepartmentCreateDTO(name=normalized_name, is_active=payload.is_active),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="department_created",
            entity_type="department",
            entity_id=department.id,
            metadata_json={"company_id": company_id, "name": department.name},
        )
        await self.session.commit()
        return DepartmentDTO.from_model(department)

    async def update_department(
        self,
        company_id: int,
        department_id: int,
        payload: DepartmentUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> DepartmentDTO:
        department = await self._get_department_or_raise(company_id, department_id)
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise DepartmentAlreadyExistsError("")

        await self.ensure_name_available(company_id, normalized_name, exclude_department_id=department.id)
        updated_department = await self.department_repo.update(
            department,
            DepartmentUpdateDTO(name=normalized_name, is_active=payload.is_active),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="department_updated",
            entity_type="department",
            entity_id=updated_department.id,
            metadata_json={"company_id": company_id, "name": updated_department.name},
        )
        await self.session.commit()
        return DepartmentDTO.from_model(updated_department)

    async def toggle_department_status(
        self,
        company_id: int,
        department_id: int,
        actor_telegram_id: int | None = None,
    ) -> DepartmentDTO:
        department = await self._get_department_or_raise(company_id, department_id)
        updated_department = await self.department_repo.update(
            department,
            DepartmentUpdateDTO(name=department.name, is_active=not department.is_active),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="department_status_toggled",
            entity_type="department",
            entity_id=updated_department.id,
            metadata_json={"company_id": company_id, "is_active": updated_department.is_active},
        )
        await self.session.commit()
        return DepartmentDTO.from_model(updated_department)

    async def delete_department(
        self,
        company_id: int,
        department_id: int,
        actor_telegram_id: int | None = None,
    ) -> None:
        department = await self._get_department_or_raise(company_id, department_id)
        linked_employees = await self.employee_repo.count_by_department(company_id, department_id)
        if linked_employees > 0:
            raise DepartmentDeleteRestrictedError()

        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="department_deleted",
            entity_type="department",
            entity_id=department.id,
            metadata_json={"company_id": company_id, "name": department.name},
        )
        await self.department_repo.delete(department)
        await self.session.commit()

    async def get_department(self, company_id: int, department_id: int) -> DepartmentDTO:
        department = await self._get_department_or_raise(company_id, department_id)
        return DepartmentDTO.from_model(department)

    async def list_departments(
        self,
        company_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> DepartmentListPageDTO:
        safe_page_size = max(1, page_size)
        departments, total_items = await self.department_repo.list_paginated(company_id, page, safe_page_size)
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            departments, total_items = await self.department_repo.list_paginated(company_id, normalized_page, safe_page_size)
        return DepartmentListPageDTO(
            items=[DepartmentDTO.from_model(department) for department in departments],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def list_department_options(self, company_id: int, *, active_only: bool = False) -> list[DepartmentDTO]:
        departments = await self.department_repo.list_by_company(company_id, active_only=active_only)
        return [DepartmentDTO.from_model(department) for department in departments]

    async def ensure_name_available(
        self,
        company_id: int,
        name: str,
        exclude_department_id: int | None = None,
    ) -> None:
        existing_department = await self.department_repo.get_by_name_in_company(company_id, name)
        if existing_department is None:
            return
        if exclude_department_id is not None and existing_department.id == exclude_department_id:
            return
        raise DepartmentAlreadyExistsError(name)

    async def _get_department_or_raise(self, company_id: int, department_id: int):
        department = await self.department_repo.get_by_id(company_id, department_id)
        if department is None:
            raise DepartmentNotFoundError(department_id)
        return department
