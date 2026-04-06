from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType

if TYPE_CHECKING:
    from app.db.models.attendance_record import AttendanceRecord
    from app.db.models.branch import Branch
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class AttendanceSession(TimestampMixin, Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    branch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("branches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_type: Mapped[AttendanceSessionType] = mapped_column(
        SqlEnum(AttendanceSessionType, name="attendance_session_type", native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[AttendanceSessionStatus] = mapped_column(
        SqlEnum(AttendanceSessionStatus, name="attendance_session_status", native_enum=False, length=32),
        nullable=False,
    )
    challenge_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_to_branch_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_location_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    video_note_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_note_file_unique_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_video_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    company: Mapped[Company] = relationship(back_populates="attendance_sessions")
    employee: Mapped[Employee] = relationship(back_populates="attendance_sessions")
    branch: Mapped[Branch] = relationship(back_populates="attendance_sessions")
    check_in_record: Mapped[AttendanceRecord | None] = relationship(
        back_populates="check_in_session",
        foreign_keys="AttendanceRecord.check_in_session_id",
    )
    check_out_record: Mapped[AttendanceRecord | None] = relationship(
        back_populates="check_out_session",
        foreign_keys="AttendanceRecord.check_out_session_id",
    )
