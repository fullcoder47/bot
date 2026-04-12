from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.company_admin_application_repo import CompanyAdminApplicationRepository
from app.domain.dto.company_dto import CompanyAdminAssignDTO, CompanyCreateDTO, CompanyDetailDTO
from app.domain.dto.public_onboarding_dto import CompanyAdminApplicationDTO
from app.domain.dto.user_dto import TelegramUserDTO
from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode
from app.domain.exceptions.company_admin_exceptions import InvalidPhoneError
from app.domain.exceptions.company_exceptions import CompanyAlreadyExistsError, CompanyNameValidationError
from app.domain.exceptions.public_onboarding_exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStateError,
    PaymentCardNotConfiguredError,
    PaymentWindowExpiredError,
)
from app.services.company_admin_service import CompanyAdminService
from app.services.company_service import CompanyService
from app.services.system_settings_service import SystemSettingsService


class PublicOnboardingService:
    PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")
    PAYMENT_WINDOW_MINUTES = 20
    DEFAULT_SUBSCRIPTION_DAYS = 30
    try:
        APP_TIMEZONE = ZoneInfo("Asia/Tashkent")
    except ZoneInfoNotFoundError:
        APP_TIMEZONE = timezone(timedelta(hours=5))

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.application_repo = CompanyAdminApplicationRepository(session)
        self.company_service = CompanyService(session)
        self.company_admin_service = CompanyAdminService(session)
        self.system_settings_service = SystemSettingsService(session)
        self.audit_log_repo = AuditLogRepository(session)

    @classmethod
    def now(cls) -> datetime:
        return datetime.now(cls.APP_TIMEZONE)

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

    async def sync_application_profile(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.create_or_update_profile(
            telegram_id=telegram_user.telegram_id,
            full_name=telegram_user.full_name,
            username=telegram_user.username,
            language=language,
        )
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def get_application_by_telegram_id(
        self,
        telegram_id: int,
    ) -> CompanyAdminApplicationDTO | None:
        application = await self.application_repo.get_by_telegram_id(telegram_id)
        if application is None:
            return None
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired
        return CompanyAdminApplicationDTO.from_model(application)

    async def get_application_by_id(self, application_id: int) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.get_by_id(application_id)
        if application is None:
            raise ApplicationNotFoundError()
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired
        return CompanyAdminApplicationDTO.from_model(application)

    async def start_application(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.create_or_update_profile(
            telegram_id=telegram_user.telegram_id,
            full_name=telegram_user.full_name,
            username=telegram_user.username,
            language=language,
        )
        if application.status in {
            CompanyAdminApplicationStatus.PAYMENT_REJECTED,
            CompanyAdminApplicationStatus.EXPIRED,
        }:
            await self.application_repo.update_status(application, CompanyAdminApplicationStatus.DRAFT)
            application.rejection_reason = None
            application.payment_deadline_at = None
            application.payment_receipt_file_id = None
            application.payment_receipt_file_unique_id = None
            application.payment_submitted_at = None
            await self.session.flush()
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def start_payment(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> tuple[CompanyAdminApplicationDTO, str]:
        payment_card = await self.system_settings_service.get_payment_card_number()
        if payment_card is None:
            raise PaymentCardNotConfiguredError()

        application = await self.application_repo.create_or_update_profile(
            telegram_id=telegram_user.telegram_id,
            full_name=telegram_user.full_name,
            username=telegram_user.username,
            language=language,
        )
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired

        if application.status in {
            CompanyAdminApplicationStatus.PAYMENT_SUBMITTED,
            CompanyAdminApplicationStatus.PAYMENT_APPROVED,
            CompanyAdminApplicationStatus.APPLICATION_REJECTED,
            CompanyAdminApplicationStatus.PENDING_FINAL_APPROVAL,
            CompanyAdminApplicationStatus.APPROVED,
        }:
            raise InvalidApplicationStateError()

        deadline_at = self.now() + timedelta(minutes=self.PAYMENT_WINDOW_MINUTES)
        application = await self.application_repo.save_payment_window(
            application,
            deadline_at=deadline_at,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=telegram_user.telegram_id,
            action="public_onboarding_payment_started",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"deadline_at": deadline_at.isoformat()},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application), payment_card

    async def submit_payment_receipt(
        self,
        telegram_id: int,
        *,
        file_id: str,
        file_unique_id: str,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.get_by_telegram_id(telegram_id)
        if application is None:
            raise ApplicationNotFoundError()
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired

        if application.status is not CompanyAdminApplicationStatus.AWAITING_PAYMENT:
            raise InvalidApplicationStateError()
        if application.payment_deadline_at is None or application.payment_deadline_at < self.now():
            raise PaymentWindowExpiredError()

        submitted_at = self.now()
        application = await self.application_repo.attach_payment_receipt(
            application,
            file_id=file_id,
            file_unique_id=file_unique_id,
            submitted_at=submitted_at,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=telegram_id,
            action="public_onboarding_payment_receipt_submitted",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"submitted_at": submitted_at.isoformat()},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def approve_payment(
        self,
        application_id: int,
        *,
        actor_telegram_id: int,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.get_by_id(application_id)
        if application is None:
            raise ApplicationNotFoundError()
        if application.status is not CompanyAdminApplicationStatus.PAYMENT_SUBMITTED:
            raise InvalidApplicationStateError()

        approved_at = self.now()
        application = await self.application_repo.mark_payment_approved(
            application,
            approved_at=approved_at,
            reviewed_by_telegram_id=actor_telegram_id,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="public_onboarding_payment_approved",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"approved_at": approved_at.isoformat()},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def reject_payment(
        self,
        application_id: int,
        *,
        actor_telegram_id: int,
        reason: str | None = None,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.get_by_id(application_id)
        if application is None:
            raise ApplicationNotFoundError()
        if application.status is not CompanyAdminApplicationStatus.PAYMENT_SUBMITTED:
            raise InvalidApplicationStateError()

        reviewed_at = self.now()
        application = await self.application_repo.mark_payment_rejected(
            application,
            reviewed_at=reviewed_at,
            reviewed_by_telegram_id=actor_telegram_id,
            rejection_reason=reason,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="public_onboarding_payment_rejected",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"reviewed_at": reviewed_at.isoformat(), "reason": reason},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def save_company_name(
        self,
        telegram_id: int,
        company_name: str,
    ) -> CompanyAdminApplicationDTO:
        application = await self._require_company_draft_access(telegram_id)
        normalized_name = await self.company_service.validate_new_company_name(company_name)
        application = await self.application_repo.save_company_name(application, normalized_name)
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def save_company_plan(
        self,
        telegram_id: int,
        plan: CompanyPlan,
    ) -> CompanyAdminApplicationDTO:
        application = await self._require_company_draft_access(telegram_id)
        application = await self.application_repo.save_company_plan(application, plan)
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def save_contact_phone(
        self,
        telegram_id: int,
        contact_phone: str | None,
    ) -> CompanyAdminApplicationDTO:
        application = await self._require_company_draft_access(telegram_id)
        application = await self.application_repo.save_contact_phone(application, contact_phone)
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def submit_final_application(self, telegram_id: int) -> CompanyAdminApplicationDTO:
        application = await self._require_company_draft_access(telegram_id)
        if not application.company_name:
            raise InvalidApplicationStateError()
        if application.company_plan is None:
            raise InvalidApplicationStateError()

        await self.company_service.ensure_name_available(application.company_name)
        submitted_at = self.now()
        application = await self.application_repo.submit_for_final_review(
            application,
            submitted_at=submitted_at,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=telegram_id,
            action="public_onboarding_application_submitted",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"submitted_at": submitted_at.isoformat()},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def approve_final_application(
        self,
        application_id: int,
        *,
        actor_telegram_id: int,
    ) -> tuple[CompanyAdminApplicationDTO, CompanyDetailDTO]:
        application = await self.application_repo.get_by_id(application_id)
        if application is None:
            raise ApplicationNotFoundError()
        if application.status is not CompanyAdminApplicationStatus.PENDING_FINAL_APPROVAL:
            raise InvalidApplicationStateError()
        if not application.company_name or application.company_plan is None:
            raise InvalidApplicationStateError()

        approved_at = self.now()
        subscription_end = approved_at + timedelta(days=self.DEFAULT_SUBSCRIPTION_DAYS)
        company = await self.company_service.create_company(
            CompanyCreateDTO(
                name=application.company_name,
                plan=application.company_plan,
                is_active=True,
                subscription_end=subscription_end,
            ),
            actor_telegram_id=actor_telegram_id,
        )
        company = await self.company_admin_service.assign_company_admin(
            CompanyAdminAssignDTO(
                company_id=company.id,
                telegram_id=application.telegram_id,
            ),
            actor_telegram_id=actor_telegram_id,
        )
        application = await self.application_repo.mark_approved(
            application,
            approved_at=approved_at,
            reviewed_by_telegram_id=actor_telegram_id,
            created_company_id=company.id,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="public_onboarding_application_approved",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={
                "approved_at": approved_at.isoformat(),
                "created_company_id": company.id,
            },
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application), company

    async def reject_final_application(
        self,
        application_id: int,
        *,
        actor_telegram_id: int,
        reason: str | None = None,
    ) -> CompanyAdminApplicationDTO:
        application = await self.application_repo.get_by_id(application_id)
        if application is None:
            raise ApplicationNotFoundError()
        if application.status is not CompanyAdminApplicationStatus.PENDING_FINAL_APPROVAL:
            raise InvalidApplicationStateError()

        reviewed_at = self.now()
        application = await self.application_repo.mark_application_rejected(
            application,
            reviewed_at=reviewed_at,
            reviewed_by_telegram_id=actor_telegram_id,
            rejection_reason=reason,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="public_onboarding_application_rejected",
            entity_type="company_admin_application",
            entity_id=application.id,
            metadata_json={"reviewed_at": reviewed_at.isoformat(), "reason": reason},
        )
        await self.session.commit()
        return CompanyAdminApplicationDTO.from_model(application)

    async def expire_if_needed(self, application) -> object | None:
        if (
            application.status is CompanyAdminApplicationStatus.AWAITING_PAYMENT
            and application.payment_deadline_at is not None
            and application.payment_deadline_at < self.now()
        ):
            expired_application = await self.application_repo.mark_expired(application)
            await self.audit_log_repo.create(
                actor_telegram_id=application.telegram_id,
                action="public_onboarding_payment_expired",
                entity_type="company_admin_application",
                entity_id=application.id,
                metadata_json={"expired_at": self.now().isoformat()},
            )
            await self.session.commit()
            return expired_application
        return None

    async def _require_company_draft_access(self, telegram_id: int):
        application = await self.application_repo.get_by_telegram_id(telegram_id)
        if application is None:
            raise ApplicationNotFoundError()
        expired = await self.expire_if_needed(application)
        if expired is not None:
            application = expired
        if application.status not in {
            CompanyAdminApplicationStatus.PAYMENT_APPROVED,
            CompanyAdminApplicationStatus.APPLICATION_REJECTED,
        }:
            raise InvalidApplicationStateError()
        return application
