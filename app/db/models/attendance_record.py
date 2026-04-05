from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.attendance_status import AttendanceStatus

if TYPE_CHECKING:
    from app.db.models.attendance_session import AttendanceSession
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class AttendanceRecord(TimestampMixin, Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_records_employee_date"),
    )

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
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    check_in_session_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("attendance_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    check_out_session_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("attendance_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        SqlEnum(AttendanceStatus, name="attendance_status", native_enum=False, length=32),
        default=AttendanceStatus.PRESENT,
        nullable=False,
    )
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    company: Mapped[Company] = relationship(back_populates="attendance_records")
    employee: Mapped[Employee] = relationship(back_populates="attendance_records")
    check_in_session: Mapped[AttendanceSession | None] = relationship(
        back_populates="check_in_record",
        foreign_keys=[check_in_session_id],
    )
    check_out_session: Mapped[AttendanceSession | None] = relationship(
        back_populates="check_out_record",
        foreign_keys=[check_out_session_id],
    )
