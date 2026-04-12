from __future__ import annotations

from datetime import datetime, time
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.employee_repo import EmployeeRepository
from app.db.repositories.shift_repo import ShiftRepository
from app.domain.dto.shift_dto import ShiftCreateDTO, ShiftDTO, ShiftListPageDTO, ShiftUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    InvalidWorkDaysError,
    ShiftAlreadyExistsError,
    ShiftNotFoundError,
)


class ShiftService:
    DEFAULT_PAGE_SIZE = 5
    VALID_WORK_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.shift_repo = ShiftRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.split()).strip()

    @staticmethod
    def parse_time_value(value: str) -> time:
        normalized = " ".join(value.split()).strip()
        return datetime.strptime(normalized, "%H:%M").time()

    @staticmethod
    def parse_minutes_value(value: str) -> int:
        normalized = " ".join(value.split()).strip()
        if not normalized.isdigit():
            raise InvalidWorkDaysError()
        return int(normalized)

    def parse_work_days(self, value: str) -> list[str]:
        normalized = " ".join(value.split()).strip()
        items = [item.strip().upper() for item in normalized.split(",") if item.strip()]
        if not items:
            raise InvalidWorkDaysError()
        if any(item not in self.VALID_WORK_DAYS for item in items):
            raise InvalidWorkDaysError()
        return items

    async def create_shift(
        self,
        company_id: int,
        payload: ShiftCreateDTO,
        actor_telegram_id: int | None = None,
    ) -> ShiftDTO:
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise ShiftAlreadyExistsError("")
        await self.ensure_name_available(company_id, normalized_name)

        shift = await self.shift_repo.create(
            company_id,
            ShiftCreateDTO(
                name=normalized_name,
                start_time=payload.start_time,
                end_time=payload.end_time,
                late_after_minutes=payload.late_after_minutes,
                early_leave_before_minutes=payload.early_leave_before_minutes,
                work_days=payload.work_days,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="shift_created",
            entity_type="shift",
            entity_id=shift.id,
            metadata_json={"company_id": company_id, "name": shift.name},
        )
        await self.session.commit()
        return ShiftDTO.from_model(shift)

    async def update_shift(
        self,
        company_id: int,
        shift_id: int,
        payload: ShiftUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> ShiftDTO:
        shift = await self._get_shift_or_raise(company_id, shift_id)
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise ShiftAlreadyExistsError("")
        await self.ensure_name_available(company_id, normalized_name, exclude_shift_id=shift.id)

        updated_shift = await self.shift_repo.update(
            shift,
            ShiftUpdateDTO(
                name=normalized_name,
                start_time=payload.start_time,
                end_time=payload.end_time,
                late_after_minutes=payload.late_after_minutes,
                early_leave_before_minutes=payload.early_leave_before_minutes,
                work_days=payload.work_days,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="shift_updated",
            entity_type="shift",
            entity_id=updated_shift.id,
            metadata_json={"company_id": company_id, "name": updated_shift.name},
        )
        await self.session.commit()
        return ShiftDTO.from_model(updated_shift)

    async def toggle_shift_status(
        self,
        company_id: int,
        shift_id: int,
        actor_telegram_id: int | None = None,
    ) -> ShiftDTO:
        shift = await self._get_shift_or_raise(company_id, shift_id)
        updated_shift = await self.shift_repo.update(
            shift,
            ShiftUpdateDTO(
                name=shift.name,
                start_time=shift.start_time,
                end_time=shift.end_time,
                late_after_minutes=shift.late_after_minutes,
                early_leave_before_minutes=shift.early_leave_before_minutes,
                work_days=list(shift.work_days),
                is_active=not shift.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="shift_status_toggled",
            entity_type="shift",
            entity_id=updated_shift.id,
            metadata_json={"company_id": company_id, "is_active": updated_shift.is_active},
        )
        await self.session.commit()
        return ShiftDTO.from_model(updated_shift)

    async def delete_shift(
        self,
        company_id: int,
        shift_id: int,
        actor_telegram_id: int | None = None,
    ) -> int:
        shift = await self._get_shift_or_raise(company_id, shift_id)
        detached_employees = await self.employee_repo.clear_shift_assignments(company_id, shift_id)

        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="shift_deleted",
            entity_type="shift",
            entity_id=shift.id,
            metadata_json={
                "company_id": company_id,
                "name": shift.name,
                "detached_employees": detached_employees,
            },
        )
        await self.shift_repo.delete(shift)
        await self.session.commit()
        return detached_employees

    async def get_shift(self, company_id: int, shift_id: int) -> ShiftDTO:
        shift = await self._get_shift_or_raise(company_id, shift_id)
        return ShiftDTO.from_model(shift)

    async def list_shifts(
        self,
        company_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> ShiftListPageDTO:
        safe_page_size = max(1, page_size)
        shifts, total_items = await self.shift_repo.list_paginated(company_id, page, safe_page_size)
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            shifts, total_items = await self.shift_repo.list_paginated(company_id, normalized_page, safe_page_size)
        return ShiftListPageDTO(
            items=[ShiftDTO.from_model(shift) for shift in shifts],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def list_shift_options(self, company_id: int, *, active_only: bool = False) -> list[ShiftDTO]:
        shifts = await self.shift_repo.list_by_company(company_id, active_only=active_only)
        return [ShiftDTO.from_model(shift) for shift in shifts]

    async def ensure_name_available(
        self,
        company_id: int,
        name: str,
        exclude_shift_id: int | None = None,
    ) -> None:
        existing_shift = await self.shift_repo.get_by_name_in_company(company_id, name)
        if existing_shift is None:
            return
        if exclude_shift_id is not None and existing_shift.id == exclude_shift_id:
            return
        raise ShiftAlreadyExistsError(name)

    async def _get_shift_or_raise(self, company_id: int, shift_id: int):
        shift = await self.shift_repo.get_by_id(company_id, shift_id)
        if shift is None:
            raise ShiftNotFoundError(shift_id)
        return shift
