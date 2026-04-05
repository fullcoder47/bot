from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.leave_status import LeaveStatus
from app.domain.enums.leave_type import LeaveType

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "leave_requests"

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
    leave_type: Mapped[LeaveType] = mapped_column(
        SqlEnum(LeaveType, name="leave_type", native_enum=False, length=32),
        nullable=False,
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        SqlEnum(LeaveStatus, name="leave_status", native_enum=False, length=32),
        default=LeaveStatus.PENDING,
        nullable=False,
    )

    company: Mapped[Company] = relationship(back_populates="leave_requests")
    employee: Mapped[Employee] = relationship(back_populates="leave_requests")
