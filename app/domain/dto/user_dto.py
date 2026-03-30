from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from aiogram.types import User as AiogramUser

from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole

if TYPE_CHECKING:
    from app.db.models.user import User


@dataclass(slots=True, frozen=True)
class TelegramUserDTO:
    telegram_id: int
    full_name: str
    username: str | None = None
    phone: str | None = None

    @classmethod
    def from_aiogram(cls, user: AiogramUser) -> "TelegramUserDTO":
        full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
        return cls(
            telegram_id=user.id,
            full_name=full_name or user.username or str(user.id),
            username=user.username,
        )


@dataclass(slots=True, frozen=True)
class CreateUserDTO:
    telegram_id: int
    full_name: str
    username: str | None = None
    phone: str | None = None
    role: UserRole = UserRole.EMPLOYEE
    language: LanguageCode | None = None
    is_active: bool = False


class StartFlowStatus(StrEnum):
    REQUEST_LANGUAGE = "request_language"
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    ACCESS_DENIED = "access_denied"


@dataclass(slots=True, frozen=True)
class UserDTO:
    id: int
    telegram_id: int
    full_name: str
    username: str | None
    phone: str | None
    role: UserRole
    language: LanguageCode | None
    is_active: bool

    @classmethod
    def from_model(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            telegram_id=user.telegram_id,
            full_name=user.full_name,
            username=user.username,
            phone=user.phone,
            role=user.role,
            language=user.language,
            is_active=user.is_active,
        )


@dataclass(slots=True, frozen=True)
class StartFlowResult:
    status: StartFlowStatus
    language: LanguageCode | None = None
    user: UserDTO | None = None
