from __future__ import annotations

from datetime import datetime, time, timezone
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.dto.company_dto import (
    CompanyCreateDTO,
    CompanyDetailDTO,
    CompanyListFiltersDTO,
    CompanyListPageDTO,
    CompanyDTO,
    CompanyUpdateDTO,
    SubscriptionUpdateDTO,
)
from app.domain.exceptions.company_exceptions import (
    CompanyAlreadyExistsError,
    CompanyNameValidationError,
    CompanyNotFoundError,
)


class CompanyService:
    DEFAULT_PAGE_SIZE = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_company_name(name: str) -> str:
        return " ".join(name.split()).strip()

    @staticmethod
    def normalize_search_query(query: str) -> str:
        return " ".join(query.split()).strip()

    @staticmethod
    def parse_subscription_date(raw_value: str) -> datetime:
        normalized_value = " ".join(raw_value.split()).strip()
        parsed_date = datetime.strptime(normalized_value, "%Y-%m-%d").date()
        return datetime.combine(parsed_date, time.max, tzinfo=timezone.utc)

    async def validate_new_company_name(self, raw_name: str) -> str:
        normalized_name = self.normalize_company_name(raw_name)
        if not normalized_name:
            raise CompanyNameValidationError()

        await self.ensure_name_available(normalized_name)
        return normalized_name

    async def ensure_name_available(
        self,
        name: str,
        exclude_company_id: int | None = None,
    ) -> None:
        existing_company = await self.company_repo.get_by_name(name)
        if existing_company is None:
            return

        if exclude_company_id is not None and existing_company.id == exclude_company_id:
            return

        raise CompanyAlreadyExistsError(name)

    async def create_company(
        self,
        payload: CompanyCreateDTO,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        normalized_name = await self.validate_new_company_name(payload.name)

        company = await self.company_repo.create(
            CompanyCreateDTO(
                name=normalized_name,
                plan=payload.plan,
                is_active=payload.is_active,
                subscription_end=payload.subscription_end,
            )
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_created",
            entity_type="company",
            entity_id=company.id,
            metadata_json={
                "name": company.name,
                "plan": company.plan.value,
                "is_active": company.is_active,
                "subscription_end": company.subscription_end.isoformat() if company.subscription_end else None,
            },
        )
        await self.session.commit()
        return await self._build_detail(company)

    async def list_companies(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: CompanyListFiltersDTO | None = None,
    ) -> CompanyListPageDTO:
        safe_page_size = max(1, page_size)
        companies, total_items = await self.company_repo.list_paginated(
            page=page,
            page_size=safe_page_size,
            filters=filters,
        )
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)

        if normalized_page != page and total_items:
            companies, total_items = await self.company_repo.list_paginated(
                page=normalized_page,
                page_size=safe_page_size,
                filters=filters,
            )

        return CompanyListPageDTO(
            items=[CompanyDTO.from_model(company) for company in companies],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def search_companies(
        self,
        query: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: CompanyListFiltersDTO | None = None,
    ) -> CompanyListPageDTO:
        normalized_query = self.normalize_search_query(query)
        search_filters = CompanyListFiltersDTO(
            search=normalized_query or None,
            is_active=filters.is_active if filters else None,
            plan=filters.plan if filters else None,
            expired_only=filters.expired_only if filters else False,
        )
        return await self.list_companies(page=page, page_size=page_size, filters=search_filters)

    async def get_company_detail(self, company_id: int) -> CompanyDetailDTO:
        company = await self._get_company_or_raise(company_id)
        return await self._build_detail(company)

    async def update_company(
        self,
        company_id: int,
        payload: CompanyUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        company = await self._get_company_or_raise(company_id)

        update_payload = CompanyUpdateDTO(
            plan=payload.plan,
            is_active=payload.is_active,
            subscription_end=payload.subscription_end,
            subscription_end_provided=payload.subscription_end_provided,
        )

        if payload.name is not None:
            normalized_name = self.normalize_company_name(payload.name)
            if not normalized_name:
                raise CompanyNameValidationError()

            await self.ensure_name_available(normalized_name, exclude_company_id=company.id)
            update_payload = CompanyUpdateDTO(
                name=normalized_name,
                plan=update_payload.plan,
                is_active=update_payload.is_active,
                subscription_end=update_payload.subscription_end,
                subscription_end_provided=update_payload.subscription_end_provided,
            )

        await self.company_repo.update(company, update_payload)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_updated",
            entity_type="company",
            entity_id=company.id,
            metadata_json={
                "name": company.name,
                "plan": company.plan.value,
                "is_active": company.is_active,
                "subscription_end": company.subscription_end.isoformat() if company.subscription_end else None,
            },
        )
        await self.session.commit()
        return await self._build_detail(company)

    async def update_subscription(
        self,
        company_id: int,
        payload: SubscriptionUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        return await self.update_company(
            company_id=company_id,
            payload=CompanyUpdateDTO(
                subscription_end=payload.subscription_end,
                subscription_end_provided=True,
            ),
            actor_telegram_id=actor_telegram_id,
        )

    async def toggle_company_status(
        self,
        company_id: int,
        actor_telegram_id: int | None = None,
    ) -> CompanyDetailDTO:
        company = await self._get_company_or_raise(company_id)
        await self.company_repo.toggle_is_active(company)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_status_toggled",
            entity_type="company",
            entity_id=company.id,
            metadata_json={"is_active": company.is_active},
        )
        await self.session.commit()
        return await self._build_detail(company)

    async def delete_company(
        self,
        company_id: int,
        actor_telegram_id: int | None = None,
    ) -> None:
        company = await self._get_company_or_raise(company_id)
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="company_deleted",
            entity_type="company",
            entity_id=company.id,
            metadata_json={"name": company.name},
        )
        await self.company_repo.delete(company)
        await self.session.commit()

    async def _get_company_or_raise(self, company_id: int) -> Company:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)
        return company

    async def _build_detail(self, company: Company) -> CompanyDetailDTO:
        invite = await self.company_admin_repo.get_by_company_id(company.id)
        return CompanyDetailDTO.from_model(company, invite)
