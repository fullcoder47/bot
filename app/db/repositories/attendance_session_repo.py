from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.attendance_session import AttendanceSession
from app.db.models.employee import Employee
from app.domain.dto.attendance_dto import AttendanceSessionCreateDTO
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType


class AttendanceSessionRepository:
    OPEN_STATUSES = (
        AttendanceSessionStatus.PENDING_LOCATION,
        AttendanceSessionStatus.PENDING_VIDEO,
    )

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: AttendanceSessionCreateDTO) -> AttendanceSession:
        attendance_session = AttendanceSession(
            company_id=payload.company_id,
            employee_id=payload.employee_id,
            branch_id=payload.branch_id,
            session_type=payload.session_type,
            status=payload.status,
            expires_at=payload.expires_at,
        )
        self.session.add(attendance_session)
        await self.session.flush()
        return attendance_session

    async def get_by_id(self, session_id: int) -> AttendanceSession | None:
        statement = (
            select(AttendanceSession)
            .options(
                joinedload(AttendanceSession.employee).joinedload(Employee.branch),
                joinedload(AttendanceSession.employee).joinedload(Employee.shift),
                joinedload(AttendanceSession.employee).joinedload(Employee.company),
                joinedload(AttendanceSession.branch),
            )
            .where(AttendanceSession.id == session_id)
        )
        return await self.session.scalar(statement)

    async def get_open_session_for_employee(self, employee_id: int) -> AttendanceSession | None:
        return await self.get_filtered_open_session_for_employee(employee_id)

    async def get_filtered_open_session_for_employee(
        self,
        employee_id: int,
        *,
        status: AttendanceSessionStatus | None = None,
        session_type: AttendanceSessionType | None = None,
    ) -> AttendanceSession | None:
        statement = (
            select(AttendanceSession)
            .options(joinedload(AttendanceSession.branch))
            .where(
                AttendanceSession.employee_id == employee_id,
                AttendanceSession.status.in_(self.OPEN_STATUSES),
            )
        )
        if status is not None:
            statement = statement.where(AttendanceSession.status == status)
        if session_type is not None:
            statement = statement.where(AttendanceSession.session_type == session_type)
        statement = statement.order_by(AttendanceSession.created_at.desc(), AttendanceSession.id.desc())
        return await self.session.scalar(statement)

    async def get_pending_session_for_employee_by_type(
        self,
        employee_id: int,
        session_type: AttendanceSessionType,
    ) -> AttendanceSession | None:
        return await self.get_filtered_open_session_for_employee(
            employee_id,
            session_type=session_type,
        )

    async def get_pending_session_for_employee(
        self,
        employee_id: int,
        *,
        status: AttendanceSessionStatus,
        session_type: AttendanceSessionType | None = None,
    ) -> AttendanceSession | None:
        return await self.get_filtered_open_session_for_employee(
            employee_id,
            status=status,
            session_type=session_type,
        )

    async def expire_old_sessions(
        self,
        *,
        now: datetime,
        employee_id: int | None = None,
    ) -> int:
        statement = select(AttendanceSession).where(
            AttendanceSession.status.in_(self.OPEN_STATUSES),
            AttendanceSession.expires_at < now,
        )
        if employee_id is not None:
            statement = statement.where(AttendanceSession.employee_id == employee_id)

        result = await self.session.scalars(statement)
        sessions = list(result.all())
        for attendance_session in sessions:
            attendance_session.status = AttendanceSessionStatus.EXPIRED
            attendance_session.failure_reason = "expired"
        await self.session.flush()
        return len(sessions)

    async def cancel_session(self, attendance_session: AttendanceSession, reason: str | None = None) -> AttendanceSession:
        attendance_session.status = AttendanceSessionStatus.CANCELLED
        attendance_session.failure_reason = reason
        await self.session.flush()
        return attendance_session

    async def save(self, attendance_session: AttendanceSession) -> AttendanceSession:
        await self.session.flush()
        return attendance_session
