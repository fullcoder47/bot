from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Enum as SqlEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=False, length=32),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    language: Mapped[LanguageCode | None] = mapped_column(
        SqlEnum(LanguageCode, name="user_language", native_enum=False, length=8),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
