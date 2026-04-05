from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.domain.dto.employee_dto import EmployeeDetailDTO
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.enums.attendance_status import AttendanceStatus

if TYPE_CHECKING:
    from app.db.models.attendance_record import AttendanceRecord
    from app.db.models.attendance_session import AttendanceSession


@dataclass(slots=True, frozen=True)
class AttendanceSessionCreateDTO:
    company_id: int
    employee_id: int
    branch_id: int
    session_type: AttendanceSessionType
    status: AttendanceSessionStatus
    expires_at: datetime


@dataclass(slots=True, frozen=True)
class AttendanceSessionDTO:
    id: int
    company_id: int
    employee_id: int
    branch_id: int
    session_type: AttendanceSessionType
    status: AttendanceSessionStatus
    challenge_code: str | None
    location_lat: float | None
    location_lon: float | None
    location_accuracy: float | None
    distance_to_branch_m: int | None
    is_location_verified: bool
    video_note_file_id: str | None
    video_note_file_unique_id: str | None
    is_video_received: bool
    expires_at: datetime
    completed_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, session: AttendanceSession) -> "AttendanceSessionDTO":
        return cls(
            id=session.id,
            company_id=session.company_id,
            employee_id=session.employee_id,
            branch_id=session.branch_id,
            session_type=session.session_type,
            status=session.status,
            challenge_code=session.challenge_code,
            location_lat=session.location_lat,
            location_lon=session.location_lon,
            location_accuracy=session.location_accuracy,
            distance_to_branch_m=session.distance_to_branch_m,
            is_location_verified=session.is_location_verified,
            video_note_file_id=session.video_note_file_id,
            video_note_file_unique_id=session.video_note_file_unique_id,
            is_video_received=session.is_video_received,
            expires_at=session.expires_at,
            completed_at=session.completed_at,
            failure_reason=session.failure_reason,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


@dataclass(slots=True, frozen=True)
class AttendanceSessionStartResultDTO:
    session: AttendanceSessionDTO
    resumed: bool


@dataclass(slots=True, frozen=True)
class AttendanceLocationResultDTO:
    session: AttendanceSessionDTO
    challenge_code: str
    distance_to_branch_m: int


@dataclass(slots=True, frozen=True)
class AttendanceRecordDTO:
    id: int
    company_id: int
    employee_id: int
    date: date
    check_in_session_id: int | None
    check_out_session_id: int | None
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: AttendanceStatus
    late_minutes: int
    early_leave_minutes: int
    worked_minutes: int
    is_suspicious: bool
    note: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, record: AttendanceRecord) -> "AttendanceRecordDTO":
        return cls(
            id=record.id,
            company_id=record.company_id,
            employee_id=record.employee_id,
            date=record.date,
            check_in_session_id=record.check_in_session_id,
            check_out_session_id=record.check_out_session_id,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            status=record.status,
            late_minutes=record.late_minutes,
            early_leave_minutes=record.early_leave_minutes,
            worked_minutes=record.worked_minutes,
            is_suspicious=record.is_suspicious,
            note=record.note,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


@dataclass(slots=True, frozen=True)
class AttendanceHistoryPageDTO:
    items: list[AttendanceRecordDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(slots=True, frozen=True)
class AttendanceTodayStatusDTO:
    company_name: str
    employee: EmployeeDetailDTO
    attendance_record: AttendanceRecordDTO | None
    open_session: AttendanceSessionDTO | None
