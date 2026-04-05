from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leave_request import LeaveRequest
from app.domain.dto.leave_dto import LeaveRequestCreateDTO


class LeaveRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: LeaveRequestCreateDTO) -> LeaveRequest:
        leave_request = LeaveRequest(
            company_id=payload.company_id,
            employee_id=payload.employee_id,
            leave_type=payload.leave_type,
            from_date=payload.from_date,
            to_date=payload.to_date,
            reason=payload.reason,
        )
        self.session.add(leave_request)
        await self.session.flush()
        return leave_request

    async def list_for_employee(
        self,
        employee_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[LeaveRequest], int]:
        count_statement = select(func.count(LeaveRequest.id)).where(LeaveRequest.employee_id == employee_id)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            select(LeaveRequest)
            .where(LeaveRequest.employee_id == employee_id)
            .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result.all()), total_items

    async def get_by_id(self, employee_id: int, leave_request_id: int) -> LeaveRequest | None:
        statement = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.id == leave_request_id,
        )
        return await self.session.scalar(statement)
