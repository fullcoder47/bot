from __future__ import annotations

import math
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.attendance_session_repo import AttendanceSessionRepository
from app.db.repositories.audit_log_repo import AuditLogRepository
from app.domain.dto.attendance_dto import (
    AttendanceLocationResultDTO,
    AttendanceSessionCreateDTO,
    AttendanceSessionDTO,
)
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.exceptions.attendance_exceptions import (
    AttendanceSessionExpiredError,
    AttendanceSessionNotFoundError,
    BranchLocationNotConfiguredError,
    LocationVerificationFailedError,
)
from app.domain.exceptions.employee_exceptions import EmployeeBranchNotAssignedError
from app.services.branch_service import BranchService


def _app_tz():
    try:
        return ZoneInfo("Asia/Tashkent")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=5))


class AttendanceSessionService:
    APP_TZ = _app_tz()
    SESSION_TTL_MINUTES = 10

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.attendance_session_repo = AttendanceSessionRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(cls.APP_TZ)

    @classmethod
    def today(cls):
        return cls.now().date()

    @staticmethod
    def generate_challenge_code() -> str:
        return f"{secrets.randbelow(900000) + 100000}"

    @staticmethod
    def haversine_distance_m(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> int:
        earth_radius_m = 6_371_000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return int(round(earth_radius_m * c))

    async def expire_old_sessions(self, employee_id: int) -> int:
        expired_count = await self.attendance_session_repo.expire_old_sessions(
            now=self.now(),
            employee_id=employee_id,
        )
        if expired_count:
            await self.session.commit()
        return expired_count

    async def get_open_session(self, employee_id: int) -> AttendanceSessionDTO | None:
        session = await self.attendance_session_repo.get_open_session_for_employee(employee_id)
        if session is None:
            return None
        return AttendanceSessionDTO.from_model(session)

    async def get_pending_session(
        self,
        employee_id: int,
        *,
        status: AttendanceSessionStatus,
        session_type: AttendanceSessionType | None = None,
    ) -> AttendanceSessionDTO | None:
        session = await self.attendance_session_repo.get_pending_session_for_employee(
            employee_id,
            status=status,
            session_type=session_type,
        )
        if session is None:
            return None
        return AttendanceSessionDTO.from_model(session)

    async def get_session_for_employee(
        self,
        employee_id: int,
        session_id: int,
    ) -> AttendanceSessionDTO:
        attendance_session = await self._get_owned_session(employee_id, session_id)
        return AttendanceSessionDTO.from_model(attendance_session)

    async def create_session(
        self,
        access: EmployeeAccessDTO,
        session_type: AttendanceSessionType,
    ) -> AttendanceSessionDTO:
        if access.employee.branch is None:
            raise EmployeeBranchNotAssignedError()

        attendance_session = await self.attendance_session_repo.create(
            AttendanceSessionCreateDTO(
                company_id=access.company.id,
                employee_id=access.employee.id,
                branch_id=access.employee.branch.id,
                session_type=session_type,
                status=AttendanceSessionStatus.PENDING_LOCATION,
                expires_at=self.now() + timedelta(minutes=self.SESSION_TTL_MINUTES),
            )
        )
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action=f"attendance_session_{session_type.value.lower()}_started",
            entity_type="attendance_session",
            entity_id=attendance_session.id,
            metadata_json={
                "company_id": access.company.id,
                "employee_id": access.employee.id,
                "branch_id": access.employee.branch.id,
            },
        )
        await self.session.commit()
        await self.session.refresh(attendance_session)
        return AttendanceSessionDTO.from_model(attendance_session)

    async def cancel_session(
        self,
        access: EmployeeAccessDTO,
        session_id: int,
        *,
        reason: str = "cancelled_by_user",
    ) -> AttendanceSessionDTO:
        attendance_session = await self._get_owned_session(access.employee.id, session_id)
        if attendance_session.status not in (
            AttendanceSessionStatus.PENDING_LOCATION,
            AttendanceSessionStatus.PENDING_VIDEO,
        ):
            raise AttendanceSessionNotFoundError()
        await self.attendance_session_repo.cancel_session(attendance_session, reason=reason)
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="attendance_session_cancelled",
            entity_type="attendance_session",
            entity_id=attendance_session.id,
            metadata_json={"session_type": attendance_session.session_type.value, "reason": reason},
        )
        await self.session.commit()
        await self.session.refresh(attendance_session)
        return AttendanceSessionDTO.from_model(attendance_session)

    async def verify_location(
        self,
        access: EmployeeAccessDTO,
        session_id: int,
        *,
        latitude: float,
        longitude: float,
        accuracy: float | None,
    ) -> AttendanceLocationResultDTO:
        attendance_session = await self._get_owned_session(access.employee.id, session_id)
        if attendance_session.status is not AttendanceSessionStatus.PENDING_LOCATION:
            raise AttendanceSessionNotFoundError()

        if attendance_session.expires_at < self.now():
            attendance_session.status = AttendanceSessionStatus.EXPIRED
            attendance_session.failure_reason = "expired"
            await self.session.commit()
            raise AttendanceSessionExpiredError()

        branch = access.employee.branch
        if branch is None:
            attendance_session.status = AttendanceSessionStatus.REJECTED
            attendance_session.failure_reason = "branch_not_assigned"
            await self.session.commit()
            raise EmployeeBranchNotAssignedError()

        if (
            branch.latitude is None
            or branch.longitude is None
        ):
            attendance_session.status = AttendanceSessionStatus.REJECTED
            attendance_session.failure_reason = "branch_location_not_configured"
            await self.session.commit()
            raise BranchLocationNotConfiguredError()

        allowed_radius_meters = (
            branch.allowed_radius_meters or BranchService.DEFAULT_ALLOWED_RADIUS_METERS
        )

        distance_to_branch_m = self.haversine_distance_m(
            latitude,
            longitude,
            branch.latitude,
            branch.longitude,
        )
        attendance_session.location_lat = latitude
        attendance_session.location_lon = longitude
        attendance_session.location_accuracy = accuracy
        attendance_session.distance_to_branch_m = distance_to_branch_m

        if distance_to_branch_m > allowed_radius_meters:
            attendance_session.status = AttendanceSessionStatus.REJECTED
            attendance_session.failure_reason = "outside_allowed_radius"
            attendance_session.is_location_verified = False
            await self.audit_log_repo.create(
                actor_telegram_id=access.user.telegram_id,
                action="attendance_location_failed",
                entity_type="attendance_session",
                entity_id=attendance_session.id,
                metadata_json={
                    "distance_to_branch_m": distance_to_branch_m,
                    "allowed_radius_meters": allowed_radius_meters,
                },
            )
            await self.session.commit()
            raise LocationVerificationFailedError()

        challenge_code = self.generate_challenge_code()
        attendance_session.challenge_code = challenge_code
        attendance_session.status = AttendanceSessionStatus.PENDING_VIDEO
        attendance_session.is_location_verified = True
        attendance_session.failure_reason = None
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="attendance_location_verified",
            entity_type="attendance_session",
            entity_id=attendance_session.id,
            metadata_json={
                "distance_to_branch_m": distance_to_branch_m,
                "allowed_radius_meters": allowed_radius_meters,
            },
        )
        await self.session.commit()
        await self.session.refresh(attendance_session)
        return AttendanceLocationResultDTO(
            session=AttendanceSessionDTO.from_model(attendance_session),
            challenge_code=challenge_code,
            distance_to_branch_m=distance_to_branch_m,
        )

    async def attach_video_note(
        self,
        access: EmployeeAccessDTO,
        session_id: int,
        *,
        file_id: str,
        file_unique_id: str,
        commit: bool = True,
    ) -> AttendanceSessionDTO:
        attendance_session = await self._get_owned_session(access.employee.id, session_id)
        if attendance_session.status is not AttendanceSessionStatus.PENDING_VIDEO:
            raise AttendanceSessionNotFoundError()

        if attendance_session.expires_at < self.now():
            attendance_session.status = AttendanceSessionStatus.EXPIRED
            attendance_session.failure_reason = "expired"
            await self.session.commit()
            raise AttendanceSessionExpiredError()

        attendance_session.video_note_file_id = file_id
        attendance_session.video_note_file_unique_id = file_unique_id
        attendance_session.is_video_received = True
        attendance_session.status = AttendanceSessionStatus.COMPLETED
        attendance_session.completed_at = self.now()
        await self.audit_log_repo.create(
            actor_telegram_id=access.user.telegram_id,
            action="attendance_video_received",
            entity_type="attendance_session",
            entity_id=attendance_session.id,
            metadata_json={"session_type": attendance_session.session_type.value},
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        await self.session.refresh(attendance_session)
        return AttendanceSessionDTO.from_model(attendance_session)

    async def _get_owned_session(self, employee_id: int, session_id: int):
        attendance_session = await self.attendance_session_repo.get_by_id(session_id)
        if attendance_session is None or attendance_session.employee_id != employee_id:
            raise AttendanceSessionNotFoundError()
        return attendance_session
