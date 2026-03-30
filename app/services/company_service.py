from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.dto.company_dto import CompanyCreateDTO, CompanyDTO, CompanyDetailDTO
from app.domain.exceptions.company_exceptions import CompanyAlreadyExistsError, CompanyNotFoundError


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.company_admin_invite_repo = CompanyAdminInviteRepository(session)

    @staticmethod
    def normalize_company_name(name: str) -> str:
        return " ".join(name.split()).strip()

    async def ensure_name_available(self, name: str) -> None:
        existing_company = await self.company_repo.get_by_name(name)
        if existing_company is not None:
            raise CompanyAlreadyExistsError(name)

    async def create_company(self, payload: CompanyCreateDTO) -> CompanyDetailDTO:
        normalized_name = self.normalize_company_name(payload.name)
        if not normalized_name:
            raise ValueError("Company name cannot be empty.")

        await self.ensure_name_available(normalized_name)

        company = await self.company_repo.create(
            CompanyCreateDTO(
                name=normalized_name,
                plan=payload.plan,
                is_active=payload.is_active,
                subscription_end=payload.subscription_end,
            )
        )
        await self.session.commit()
        return CompanyDetailDTO.from_model(company)

    async def list_companies(self) -> list[CompanyDTO]:
        companies = await self.company_repo.list_all()
        return [CompanyDTO.from_model(company) for company in companies]

    async def get_company_detail(self, company_id: int) -> CompanyDetailDTO:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)

        invite = await self.company_admin_invite_repo.get_by_company_id(company_id)
        return CompanyDetailDTO.from_model(company, invite)

    async def toggle_company_status(self, company_id: int) -> CompanyDetailDTO:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise CompanyNotFoundError(company_id)

        await self.company_repo.toggle_is_active(company)
        await self.session.commit()
        invite = await self.company_admin_invite_repo.get_by_company_id(company_id)
        return CompanyDetailDTO.from_model(company, invite)
