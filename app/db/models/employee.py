from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.attendance_record import AttendanceRecord
    from app.db.models.attendance_session import AttendanceSession
    from app.db.models.branch import Branch
    from app.db.models.company import Company
    from app.db.models.department import Department
    from app.db.models.leave_request import LeaveRequest
    from app.db.models.shift import Shift
    from app.db.models.user import User


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_code", name="uq_employees_company_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    employee_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    shift_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("shifts.id", ondelete="SET NULL"),
        nullable=True,
    )
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="employees")
    user: Mapped[User | None] = relationship()
    branch: Mapped[Branch | None] = relationship(back_populates="employees")
    department: Mapped[Department | None] = relationship(back_populates="employees")
    shift: Mapped[Shift | None] = relationship(back_populates="employees")
    attendance_sessions: Mapped[list[AttendanceSession]] = relationship(back_populates="employee")
    attendance_records: Mapped[list[AttendanceRecord]] = relationship(back_populates="employee")
    leave_requests: Mapped[list[LeaveRequest]] = relationship(back_populates="employee")
