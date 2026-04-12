from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.company_admin_application import CompanyAdminApplication
from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode


class CompanyAdminApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, application_id: int) -> CompanyAdminApplication | None:
        statement = (
            select(CompanyAdminApplication)
            .options(joinedload(CompanyAdminApplication.created_company))
            .where(CompanyAdminApplication.id == application_id)
        )
        return await self.session.scalar(statement)

    async def get_by_telegram_id(self, telegram_id: int) -> CompanyAdminApplication | None:
        statement = (
            select(CompanyAdminApplication)
            .options(joinedload(CompanyAdminApplication.created_company))
            .where(CompanyAdminApplication.telegram_id == telegram_id)
        )
        return await self.session.scalar(statement)

    async def create_or_update_profile(
        self,
        *,
        telegram_id: int,
        full_name: str,
        username: str | None,
        language: LanguageCode,
    ) -> CompanyAdminApplication:
        application = await self.get_by_telegram_id(telegram_id)
        if application is None:
            application = CompanyAdminApplication(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                language=language,
                status=CompanyAdminApplicationStatus.DRAFT,
            )
            self.session.add(application)
        else:
            application.full_name = full_name
            application.username = username
            application.language = language
        await self.session.flush()
        return application

    async def update_status(
        self,
        application: CompanyAdminApplication,
        status: CompanyAdminApplicationStatus,
    ) -> CompanyAdminApplication:
        application.status = status
        await self.session.flush()
        return application

    async def save_payment_window(
        self,
        application: CompanyAdminApplication,
        *,
        deadline_at,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.AWAITING_PAYMENT
        application.payment_deadline_at = deadline_at
        application.payment_receipt_file_id = None
        application.payment_receipt_file_unique_id = None
        application.payment_submitted_at = None
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def attach_payment_receipt(
        self,
        application: CompanyAdminApplication,
        *,
        file_id: str,
        file_unique_id: str,
        submitted_at,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.PAYMENT_SUBMITTED
        application.payment_receipt_file_id = file_id
        application.payment_receipt_file_unique_id = file_unique_id
        application.payment_submitted_at = submitted_at
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def mark_payment_approved(
        self,
        application: CompanyAdminApplication,
        *,
        approved_at,
        reviewed_by_telegram_id: int,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.PAYMENT_APPROVED
        application.payment_approved_at = approved_at
        application.reviewed_at = approved_at
        application.reviewed_by_telegram_id = reviewed_by_telegram_id
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def mark_payment_rejected(
        self,
        application: CompanyAdminApplication,
        *,
        reviewed_at,
        reviewed_by_telegram_id: int,
        rejection_reason: str | None,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.PAYMENT_REJECTED
        application.reviewed_at = reviewed_at
        application.reviewed_by_telegram_id = reviewed_by_telegram_id
        application.rejection_reason = rejection_reason
        application.payment_approved_at = None
        await self.session.flush()
        return application

    async def save_company_name(
        self,
        application: CompanyAdminApplication,
        company_name: str,
    ) -> CompanyAdminApplication:
        application.company_name = company_name
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def save_company_plan(
        self,
        application: CompanyAdminApplication,
        plan: CompanyPlan,
    ) -> CompanyAdminApplication:
        application.company_plan = plan
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def save_contact_phone(
        self,
        application: CompanyAdminApplication,
        contact_phone: str | None,
    ) -> CompanyAdminApplication:
        application.contact_phone = contact_phone
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def submit_for_final_review(
        self,
        application: CompanyAdminApplication,
        *,
        submitted_at,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.PENDING_FINAL_APPROVAL
        application.submitted_at = submitted_at
        application.reviewed_at = None
        application.reviewed_by_telegram_id = None
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def mark_application_rejected(
        self,
        application: CompanyAdminApplication,
        *,
        reviewed_at,
        reviewed_by_telegram_id: int,
        rejection_reason: str | None,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.APPLICATION_REJECTED
        application.reviewed_at = reviewed_at
        application.reviewed_by_telegram_id = reviewed_by_telegram_id
        application.rejection_reason = rejection_reason
        await self.session.flush()
        return application

    async def mark_approved(
        self,
        application: CompanyAdminApplication,
        *,
        approved_at,
        reviewed_by_telegram_id: int,
        created_company_id: int,
    ) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.APPROVED
        application.reviewed_at = approved_at
        application.reviewed_by_telegram_id = reviewed_by_telegram_id
        application.created_company_id = created_company_id
        application.rejection_reason = None
        await self.session.flush()
        return application

    async def mark_expired(self, application: CompanyAdminApplication) -> CompanyAdminApplication:
        application.status = CompanyAdminApplicationStatus.EXPIRED
        application.rejection_reason = None
        await self.session.flush()
        return application
