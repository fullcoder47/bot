from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.domain.enums.leave_status import LeaveStatus
from app.domain.enums.leave_type import LeaveType

if TYPE_CHECKING:
    from app.db.models.leave_request import LeaveRequest


@dataclass(slots=True, frozen=True)
class LeaveRequestCreateDTO:
    company_id: int
    employee_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    reason: str


@dataclass(slots=True, frozen=True)
class LeaveRequestDTO:
    id: int
    company_id: int
    employee_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    reason: str
    status: LeaveStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, leave_request: LeaveRequest) -> "LeaveRequestDTO":
        return cls(
            id=leave_request.id,
            company_id=leave_request.company_id,
            employee_id=leave_request.employee_id,
            leave_type=leave_request.leave_type,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )


@dataclass(slots=True, frozen=True)
class LeaveRequestListPageDTO:
    items: list[LeaveRequestDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int
