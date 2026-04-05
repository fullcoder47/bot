from __future__ import annotations

from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.leave_request_repo import LeaveRequestRepository
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.dto.leave_dto import LeaveRequestCreateDTO, LeaveRequestDTO, LeaveRequestListPageDTO
from app.domain.exceptions.attendance_exceptions import LeaveRequestValidationError


class LeaveService:
    DEFAULT_PAGE_SIZE = 10

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.leave_request_repo = LeaveRequestRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    async def create_leave_request(
        self,
        access: EmployeeAccessDTO,
        payload: LeaveRequestCreateDTO,
    ) -> LeaveRequestDTO:
        reason = " ".join(payload.reason.split()).strip()
        if not reason:
            raise LeaveRequestValidationError("Leave reason cannot be empty.")
        if payload.from_date > payload.to_date:
            raise LeaveRequestValidationError("Leave dates are invalid.")

        leave_request = await self.leave_request_repo.create(
            LeaveRequestCreateDTO(
                company_id=access.company.id,
                employee_id=access.employee.id,
                leave_type=payload.leave_type,
                from_date=payload.from_date,
                to_date=payload.to_date,
                reason=reason,
            )
        )
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="leave_request_created",
            entity_type="leave_request",
            entity_id=leave_request.id,
            metadata_json={
                "leave_type": leave_request.leave_type.value,
                "from_date": leave_request.from_date.isoformat(),
                "to_date": leave_request.to_date.isoformat(),
            },
        )
        await self.session.commit()
        return LeaveRequestDTO.from_model(leave_request)

    async def list_employee_leave_requests(
        self,
        access: EmployeeAccessDTO,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> LeaveRequestListPageDTO:
        safe_page_size = max(1, page_size)
        leave_requests, total_items = await self.leave_request_repo.list_for_employee(
            access.employee.id,
            page,
            safe_page_size,
        )
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            leave_requests, total_items = await self.leave_request_repo.list_for_employee(
                access.employee.id,
                normalized_page,
                safe_page_size,
            )
        return LeaveRequestListPageDTO(
            items=[LeaveRequestDTO.from_model(item) for item in leave_requests],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
