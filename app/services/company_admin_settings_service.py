from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.company_dto import CompanyDetailDTO
from app.domain.dto.user_dto import UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.exceptions.company_admin_exceptions import InvalidPhoneError
from app.domain.exceptions.company_exceptions import CompanyNotFoundError


class CompanyAdminSettingsService:
    PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @classmethod
    def parse_optional_phone(cls, value: str) -> str | None:
        normalized = cls.normalize_text(value)
        if not normalized or normalized == "-":
            return None
        if not cls.PHONE_PATTERN.fullmatch(normalized):
            raise InvalidPhoneError()
        return normalized

    async def get_company_detail(self, company_id: int) -> CompanyDetailDTO:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)
        invite = await self.company_admin_repo.get_by_company_id(company_id)
        return CompanyDetailDTO.from_model(company, invite)

    async def update_language(
        self,
        telegram_id: int,
        language: LanguageCode,
        *,
        actor_telegram_id: int | None = None,
    ) -> UserDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise ValueError("user_not_found")

        previous_language = user.language.value if user.language is not None else None
        await self.user_repo.update_language(user, language)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id or telegram_id,
            action="company_admin_language_updated",
            entity_type="user",
            entity_id=user.id,
            metadata_json={
                "telegram_id": telegram_id,
                "previous_language": previous_language,
                "new_language": language.value,
            },
        )
        await self.session.commit()
        return UserDTO.from_model(user)

    async def update_phone(
        self,
        telegram_id: int,
        phone: str | None,
        *,
        actor_telegram_id: int | None = None,
    ) -> UserDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise ValueError("user_not_found")

        previous_phone = user.phone
        await self.user_repo.update_phone(user, phone)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id or telegram_id,
            action="company_admin_phone_updated",
            entity_type="user",
            entity_id=user.id,
            metadata_json={
                "telegram_id": telegram_id,
                "previous_phone": previous_phone,
                "new_phone": phone,
            },
        )
        await self.session.commit()
        return UserDTO.from_model(user)
