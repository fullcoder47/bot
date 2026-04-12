from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode

if TYPE_CHECKING:
    from app.db.models.company_admin_application import CompanyAdminApplication


@dataclass(slots=True, frozen=True)
class CompanyAdminApplicationDTO:
    id: int
    telegram_id: int
    full_name: str
    username: str | None
    language: LanguageCode
    status: CompanyAdminApplicationStatus
    company_name: str | None
    company_plan: CompanyPlan | None
    contact_phone: str | None
    payment_deadline_at: datetime | None
    payment_receipt_file_id: str | None
    payment_receipt_file_unique_id: str | None
    payment_submitted_at: datetime | None
    payment_approved_at: datetime | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_telegram_id: int | None
    rejection_reason: str | None
    created_company_id: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, application: CompanyAdminApplication) -> "CompanyAdminApplicationDTO":
        return cls(
            id=application.id,
            telegram_id=application.telegram_id,
            full_name=application.full_name,
            username=application.username,
            language=application.language,
            status=application.status,
            company_name=application.company_name,
            company_plan=application.company_plan,
            contact_phone=application.contact_phone,
            payment_deadline_at=application.payment_deadline_at,
            payment_receipt_file_id=application.payment_receipt_file_id,
            payment_receipt_file_unique_id=application.payment_receipt_file_unique_id,
            payment_submitted_at=application.payment_submitted_at,
            payment_approved_at=application.payment_approved_at,
            submitted_at=application.submitted_at,
            reviewed_at=application.reviewed_at,
            reviewed_by_telegram_id=application.reviewed_by_telegram_id,
            rejection_reason=application.rejection_reason,
            created_company_id=application.created_company_id,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
