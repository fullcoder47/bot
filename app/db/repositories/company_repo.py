from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.domain.dto.company_dto import CompanyCreateDTO


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

    async def list_all(self) -> list[Company]:
        statement = select(Company).order_by(Company.name.asc())
        result = await self.session.scalars(statement)
        return list(result.all())

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

    async def toggle_is_active(self, company: Company) -> Company:
        company.is_active = not company.is_active
        await self.session.flush()
        return company
