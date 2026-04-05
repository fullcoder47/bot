from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SqlEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.company_plan import CompanyPlan

if TYPE_CHECKING:
    from app.db.models.attendance_record import AttendanceRecord
    from app.db.models.attendance_session import AttendanceSession
    from app.db.models.branch import Branch
    from app.db.models.company_admin_invite import CompanyAdminInvite
    from app.db.models.department import Department
    from app.db.models.employee import Employee
    from app.db.models.leave_request import LeaveRequest
    from app.db.models.shift import Shift


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    plan: Mapped[CompanyPlan] = mapped_column(
        SqlEnum(CompanyPlan, name="company_plan", native_enum=False, length=32),
        default=CompanyPlan.BASIC,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscription_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    admin_invite: Mapped[CompanyAdminInvite | None] = relationship(
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )
    branches: Mapped[list[Branch]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    departments: Mapped[list[Department]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    shifts: Mapped[list[Shift]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    employees: Mapped[list[Employee]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    attendance_sessions: Mapped[list[AttendanceSession]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    attendance_records: Mapped[list[AttendanceRecord]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    leave_requests: Mapped[list[LeaveRequest]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
