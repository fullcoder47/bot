from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.domain.dto.company_dto import CompanyCreateDTO, CompanyUpdateDTO


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, company_id: int) -> Company | None:
        statement = select(Company).where(Company.id == company_id)
        return await self.session.scalar(statement)

    async def get_by_name(self, name: str) -> Company | None:
        normalized_name = name.strip().lower()
        statement = select(Company).where(func.lower(Company.name) == normalized_name)
        return await self.session.scalar(statement)

    async def list_page(self, page: int, page_size: int) -> list[Company]:
        offset = (page - 1) * page_size
        statement = (
            select(Company)
            .order_by(Company.name.asc(), Company.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def count_all(self) -> int:
        statement = select(func.count(Company.id))
        return int((await self.session.scalar(statement)) or 0)

    async def count_by_status(self, is_active: bool) -> int:
        statement = select(func.count(Company.id)).where(Company.is_active.is_(is_active))
        return int((await self.session.scalar(statement)) or 0)

    async def create(self, payload: CompanyCreateDTO) -> Company:
        company = Company(
            name=payload.name,
            plan=payload.plan,
            is_active=payload.is_active,
            subscription_end=payload.subscription_end,
        )
        self.session.add(company)
        await self.session.flush()
        return company

    async def update(self, company: Company, payload: CompanyUpdateDTO) -> Company:
        if payload.name is not None:
            company.name = payload.name
        if payload.plan is not None:
            company.plan = payload.plan
        if payload.is_active is not None:
            company.is_active = payload.is_active
        if payload.subscription_end_provided:
            company.subscription_end = payload.subscription_end
        await self.session.flush()
        return company

    async def toggle_is_active(self, company: Company) -> Company:
        company.is_active = not company.is_active
        await self.session.flush()
        return company

    async def delete(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.flush()
