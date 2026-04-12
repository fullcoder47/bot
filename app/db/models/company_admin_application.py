from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode

if TYPE_CHECKING:
    from app.db.models.company import Company


class CompanyAdminApplication(TimestampMixin, Base):
    __tablename__ = "company_admin_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[LanguageCode] = mapped_column(
        SqlEnum(LanguageCode, name="company_admin_application_language", native_enum=False, length=16),
        nullable=False,
    )
    status: Mapped[CompanyAdminApplicationStatus] = mapped_column(
        SqlEnum(
            CompanyAdminApplicationStatus,
            name="company_admin_application_status",
            native_enum=False,
            length=64,
        ),
        default=CompanyAdminApplicationStatus.DRAFT,
        nullable=False,
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_plan: Mapped[CompanyPlan | None] = mapped_column(
        SqlEnum(CompanyPlan, name="company_admin_application_plan", native_enum=False, length=32),
        nullable=True,
    )
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_receipt_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_receipt_file_unique_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_company_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_company: Mapped[Company | None] = relationship()
