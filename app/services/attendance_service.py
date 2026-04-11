from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from math import ceil
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.attendance_record_repo import AttendanceRecordRepository
from app.db.repositories.audit_log_repo import AuditLogRepository
from app.domain.dto.attendance_dto import (
    AttendanceHistoryPageDTO,
    AttendanceRecordDTO,
    AttendanceSessionDTO,
    AttendanceSessionStartResultDTO,
    AttendanceTodayStatusDTO,
)
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.enums.attendance_status import AttendanceStatus
from app.domain.exceptions.attendance_exceptions import (
    AttendanceAlreadyCheckedInError,
    AttendanceAlreadyCheckedOutError,
    AttendanceCheckOutWithoutCheckInError,
    AttendanceSessionConflictError,
    AttendanceSessionNotFoundError,
    BranchLocationNotConfiguredError,
)
from app.domain.exceptions.auth_exceptions import AccessDeniedError
from app.domain.exceptions.employee_exceptions import (
    EmployeeBranchNotAssignedError,
    EmployeeInactiveError,
    EmployeeShiftNotAssignedError,
)
from app.services.attendance_session_service import AttendanceSessionService
from app.services.employee_service import EmployeeService


def _app_tz():
    try:
        return ZoneInfo("Asia/Tashkent")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=5))


class AttendanceService:
    APP_TZ = _app_tz()
    HISTORY_PAGE_SIZE = 10

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.employee_service = EmployeeService(session)
        self.attendance_record_repo = AttendanceRecordRepository(session)
        self.attendance_session_service = AttendanceSessionService(session)
        self.audit_log_repo = AuditLogRepository(session)

    logger = logging.getLogger(__name__)

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(cls.APP_TZ)

    async def start_check_in(self, access: EmployeeAccessDTO) -> AttendanceSessionStartResultDTO:
        await self.attendance_session_service.expire_old_sessions(access.employee.id)
        open_session = await self.attendance_session_service.get_open_session(access.employee.id)
        if open_session is not None:
            return AttendanceSessionStartResultDTO(session=open_session, resumed=True)

        await self._ensure_attendance_ready(access)
        today = self.attendance_session_service.today()
        if await self.attendance_record_repo.exists_check_in_today(access.employee.id, today):
            raise AttendanceAlreadyCheckedInError()

        session = await self.attendance_session_service.create_session(access, AttendanceSessionType.CHECK_IN)
        return AttendanceSessionStartResultDTO(session=session, resumed=False)

    async def start_check_out(self, access: EmployeeAccessDTO) -> AttendanceSessionStartResultDTO:
        await self.attendance_session_service.expire_old_sessions(access.employee.id)
        open_session = await self.attendance_session_service.get_open_session(access.employee.id)
        if open_session is not None:
            return AttendanceSessionStartResultDTO(session=open_session, resumed=True)

        await self._ensure_attendance_ready(access)
        today_record = await self.attendance_record_repo.get_today_for_employee(
            access.employee.id,
            self.attendance_session_service.today(),
        )
        if today_record is None or today_record.check_in_time is None:
            raise AttendanceCheckOutWithoutCheckInError()
        if today_record.check_out_time is not None:
            raise AttendanceAlreadyCheckedOutError()

        session = await self.attendance_session_service.create_session(access, AttendanceSessionType.CHECK_OUT)
        return AttendanceSessionStartResultDTO(session=session, resumed=False)

    async def get_open_session(self, access: EmployeeAccessDTO) -> AttendanceSessionDTO | None:
        await self.attendance_session_service.expire_old_sessions(access.employee.id)
        return await self.attendance_session_service.get_open_session(access.employee.id)

    async def get_pending_session(
        self,
        access: EmployeeAccessDTO,
        *,
        status,
        session_type: AttendanceSessionType | None = None,
    ) -> AttendanceSessionDTO | None:
        await self.attendance_session_service.expire_old_sessions(access.employee.id)
        return await self.attendance_session_service.get_pending_session(
            access.employee.id,
            status=status,
            session_type=session_type,
        )

    async def cancel_open_session(self, access: EmployeeAccessDTO, session_id: int) -> AttendanceSessionDTO:
        return await self.attendance_session_service.cancel_session(access, session_id)

    async def submit_location(
        self,
        access: EmployeeAccessDTO,
        session_id: int,
        *,
        latitude: float,
        longitude: float,
        accuracy: float | None,
    ):
        return await self.attendance_session_service.verify_location(
            access,
            session_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )

    async def submit_video_note(
        self,
        access: EmployeeAccessDTO,
        session_id: int,
        *,
        file_id: str,
        file_unique_id: str,
    ) -> tuple[AttendanceSessionDTO, AttendanceRecordDTO]:
        try:
            self.logger.info(
                "Attendance video finalization started: telegram_id=%s employee_id=%s session_id=%s",
                access.user.telegram_id,
                access.employee.id,
                session_id,
            )
            session = await self.attendance_session_service.attach_video_note(
                access,
                session_id,
                file_id=file_id,
                file_unique_id=file_unique_id,
                commit=False,
            )
            if session.session_type is AttendanceSessionType.CHECK_IN:
                await self._finalize_check_in(access, session, commit=False)
            else:
                await self._finalize_check_out(access, session, commit=False)
            await self.session.commit()
            persisted_session = await self.attendance_session_service.get_session_for_employee(
                access.employee.id,
                session_id,
            )
            persisted_record = await self.attendance_record_repo.get_today_for_employee(
                access.employee.id,
                self.attendance_session_service.today(),
            )
            if persisted_record is None:
                raise AttendanceSessionConflictError()
            self.logger.info(
                "Attendance video finalization completed: telegram_id=%s employee_id=%s session_id=%s record_id=%s",
                access.user.telegram_id,
                access.employee.id,
                session_id,
                persisted_record.id,
            )
            return persisted_session, AttendanceRecordDTO.from_model(persisted_record)
        except Exception:
            self.logger.exception(
                "Attendance video finalization failed for telegram_id=%s employee_id=%s session_id=%s",
                access.user.telegram_id,
                access.employee.id,
                session_id,
            )
            await self.session.rollback()
            raise

    async def get_today_status(self, access: EmployeeAccessDTO) -> AttendanceTodayStatusDTO:
        await self.attendance_session_service.expire_old_sessions(access.employee.id)
        record = await self.attendance_record_repo.get_today_for_employee(
            access.employee.id,
            self.attendance_session_service.today(),
        )
        open_session = await self.attendance_session_service.get_open_session(access.employee.id)
        return AttendanceTodayStatusDTO(
            company_name=access.company.name,
            employee=access.employee,
            attendance_record=AttendanceRecordDTO.from_model(record) if record is not None else None,
            open_session=open_session,
        )

    async def get_history(
        self,
        access: EmployeeAccessDTO,
        *,
        page: int = 1,
        page_size: int = HISTORY_PAGE_SIZE,
    ) -> AttendanceHistoryPageDTO:
        safe_page_size = max(1, page_size)
        records, total_items = await self.attendance_record_repo.list_history_paginated(
            access.employee.id,
            page,
            safe_page_size,
        )
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            records, total_items = await self.attendance_record_repo.list_history_paginated(
                access.employee.id,
                normalized_page,
                safe_page_size,
            )
        return AttendanceHistoryPageDTO(
            items=[AttendanceRecordDTO.from_model(record) for record in records],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def get_history_record(
        self,
        access: EmployeeAccessDTO,
        record_id: int,
    ) -> AttendanceRecordDTO:
        record = await self.attendance_record_repo.get_by_id(access.employee.id, record_id)
        if record is None:
            raise AttendanceSessionNotFoundError()
        return AttendanceRecordDTO.from_model(record)

    async def _ensure_attendance_ready(self, access: EmployeeAccessDTO) -> None:
        if not access.company.is_active:
            raise AccessDeniedError(access.user.language)
        if not access.employee.is_active:
            raise EmployeeInactiveError()
        if access.employee.branch is None or not access.employee.branch.is_active:
            raise EmployeeBranchNotAssignedError()
        if access.employee.shift is None or not access.employee.shift.is_active:
            raise EmployeeShiftNotAssignedError()
        if not await self.employee_service.branch_has_valid_location(access.company.id, access.employee.id):
            raise BranchLocationNotConfiguredError()

    async def _finalize_check_in(
        self,
        access: EmployeeAccessDTO,
        session: AttendanceSessionDTO,
        *,
        commit: bool = True,
    ) -> AttendanceRecordDTO:
        today = self.attendance_session_service.today()
        record = await self.attendance_record_repo.get_today_for_employee(access.employee.id, today)
        if record is None:
            record = await self.attendance_record_repo.create(
                company_id=access.company.id,
                employee_id=access.employee.id,
                target_date=today,
            )
        if record.check_in_time is not None:
            raise AttendanceAlreadyCheckedInError()

        completed_at = session.completed_at or self.now()
        late_minutes = self._calculate_late_minutes(access, completed_at)
        record.check_in_time = completed_at
        record.check_in_session_id = session.id
        record.late_minutes = late_minutes
        record.status = AttendanceStatus.LATE if late_minutes > 0 else AttendanceStatus.PRESENT
        record.note = None
        await self.attendance_record_repo.update(record)
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="attendance_check_in_completed",
            entity_type="attendance_record",
            entity_id=record.id,
            metadata_json={"session_id": session.id, "late_minutes": late_minutes},
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        await self.session.refresh(record)
        return AttendanceRecordDTO.from_model(record)

    async def _finalize_check_out(
        self,
        access: EmployeeAccessDTO,
        session: AttendanceSessionDTO,
        *,
        commit: bool = True,
    ) -> AttendanceRecordDTO:
        today = self.attendance_session_service.today()
        record = await self.attendance_record_repo.get_today_for_employee(access.employee.id, today)
        if record is None or record.check_in_time is None:
            raise AttendanceCheckOutWithoutCheckInError()
        if record.check_out_time is not None:
            raise AttendanceAlreadyCheckedOutError()

        completed_at = session.completed_at or self.now()
        worked_minutes = max(0, int((completed_at - record.check_in_time).total_seconds() // 60))
        early_leave_minutes = self._calculate_early_leave_minutes(access, completed_at)
        record.check_out_time = completed_at
        record.check_out_session_id = session.id
        record.worked_minutes = worked_minutes
        record.early_leave_minutes = early_leave_minutes
        if early_leave_minutes > 0:
            record.status = AttendanceStatus.EARLY_LEAVE
        elif record.status is not AttendanceStatus.LATE:
            record.status = AttendanceStatus.PRESENT
        await self.attendance_record_repo.update(record)
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="attendance_check_out_completed",
            entity_type="attendance_record",
            entity_id=record.id,
            metadata_json={
                "session_id": session.id,
                "worked_minutes": worked_minutes,
                "early_leave_minutes": early_leave_minutes,
            },
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        await self.session.refresh(record)
        return AttendanceRecordDTO.from_model(record)

    @staticmethod
    def _calculate_late_minutes(access: EmployeeAccessDTO, check_in_time: datetime) -> int:
        shift = access.employee.shift
        if shift is None:
            return 0
        shift_start = datetime.combine(check_in_time.date(), shift.start_time, tzinfo=check_in_time.tzinfo)
        threshold = shift_start + timedelta(minutes=shift.late_after_minutes)
        if check_in_time <= threshold:
            return 0
        return max(0, int((check_in_time - shift_start).total_seconds() // 60))

    @staticmethod
    def _calculate_early_leave_minutes(access: EmployeeAccessDTO, check_out_time: datetime) -> int:
        shift = access.employee.shift
        if shift is None:
            return 0

        shift_start = datetime.combine(check_out_time.date(), shift.start_time, tzinfo=check_out_time.tzinfo)
        shift_end = datetime.combine(check_out_time.date(), shift.end_time, tzinfo=check_out_time.tzinfo)
        if shift_end <= shift_start:
            shift_end += timedelta(days=1)
        threshold = shift_end - timedelta(minutes=shift.early_leave_before_minutes)
        if check_out_time >= threshold:
            return 0
        return max(0, int((shift_end - check_out_time).total_seconds() // 60))
