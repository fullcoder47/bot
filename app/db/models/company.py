from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SqlEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.company_plan import CompanyPlan

if TYPE_CHECKING:
    from app.db.models.company_admin_invite import CompanyAdminInvite


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
