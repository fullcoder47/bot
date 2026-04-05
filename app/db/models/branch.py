from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.attendance_session import AttendanceSession
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class Branch(TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_branches_company_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_radius_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_location_strict: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="branches")
    employees: Mapped[list[Employee]] = relationship(back_populates="branch")
    attendance_sessions: Mapped[list[AttendanceSession]] = relationship(back_populates="branch")
