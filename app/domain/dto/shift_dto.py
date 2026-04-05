from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.shift import Shift


@dataclass(slots=True, frozen=True)
class ShiftCreateDTO:
    name: str
    start_time: time
    end_time: time
    late_after_minutes: int
    early_leave_before_minutes: int
    work_days: list[str]
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class ShiftUpdateDTO:
    name: str
    start_time: time
    end_time: time
    late_after_minutes: int
    early_leave_before_minutes: int
    work_days: list[str]
    is_active: bool


@dataclass(slots=True, frozen=True)
class ShiftDTO:
    id: int
    company_id: int
    name: str
    start_time: time
    end_time: time
    late_after_minutes: int
    early_leave_before_minutes: int
    work_days: list[str]
    is_active: bool

    @classmethod
    def from_model(cls, shift: Shift) -> "ShiftDTO":
        return cls(
            id=shift.id,
            company_id=shift.company_id,
            name=shift.name,
            start_time=shift.start_time,
            end_time=shift.end_time,
            late_after_minutes=shift.late_after_minutes,
            early_leave_before_minutes=shift.early_leave_before_minutes,
            work_days=list(shift.work_days),
            is_active=shift.is_active,
        )


@dataclass(slots=True, frozen=True)
class ShiftListPageDTO:
    items: list[ShiftDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int
