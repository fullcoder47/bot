from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum as SqlEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums.role import UserRole

if TYPE_CHECKING:
    from app.db.models.company import Company


class CompanyAdminInvite(TimestampMixin, Base):
    __tablename__ = "company_admin_invites"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_company_admin_invites_company_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="company_admin_role", native_enum=False, length=32),
        default=UserRole.COMPANY_ADMIN,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="admin_invite")
