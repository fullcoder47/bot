from __future__ import annotations

from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.dto.company_dto import (
    CompanyCreateDTO,
    CompanyDetailDTO,
    CompanyDTO,
    CompanyListPageDTO,
    CompanyUpdateDTO,
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
        self.company_admin_invite_repo = CompanyAdminInviteRepository(session)

    @staticmethod
    def normalize_company_name(name: str) -> str:
        return " ".join(name.split()).strip()

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

    async def create_company(self, payload: CompanyCreateDTO) -> CompanyDetailDTO:
        normalized_name = await self.validate_new_company_name(payload.name)

        company = await self.company_repo.create(
            CompanyCreateDTO(
                name=normalized_name,
                plan=payload.plan,
                is_active=payload.is_active,
                subscription_end=payload.subscription_end,
            )
        )
        await self.session.commit()
        return await self._build_detail(company)

    async def list_companies(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CompanyListPageDTO:
        safe_page_size = max(1, page_size)
        total_items = await self.company_repo.count_all()
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)

        companies = await self.company_repo.list_page(normalized_page, safe_page_size)
        return CompanyListPageDTO(
            items=[CompanyDTO.from_model(company) for company in companies],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def get_company_detail(self, company_id: int) -> CompanyDetailDTO:
        company = await self._get_company_or_raise(company_id)
        return await self._build_detail(company)

    async def update_company(
        self,
        company_id: int,
        payload: CompanyUpdateDTO,
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
        await self.session.commit()
        return await self._build_detail(company)

    async def toggle_company_status(self, company_id: int) -> CompanyDetailDTO:
        company = await self._get_company_or_raise(company_id)
        await self.company_repo.toggle_is_active(company)
        await self.session.commit()
        return await self._build_detail(company)

    async def delete_company(self, company_id: int) -> None:
        company = await self._get_company_or_raise(company_id)
        await self.company_repo.delete(company)
        await self.session.commit()

    async def _get_company_or_raise(self, company_id: int) -> Company:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)
        return company

    async def _build_detail(self, company: Company) -> CompanyDetailDTO:
        invite = await self.company_admin_invite_repo.get_by_company_id(company.id)
        return CompanyDetailDTO.from_model(company, invite)
