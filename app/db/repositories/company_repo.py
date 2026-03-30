from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.domain.dto.company_dto import CompanyCreateDTO, CompanyListFiltersDTO, CompanyUpdateDTO
from app.domain.enums.company_plan import CompanyPlan


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

    async def delete(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.flush()

    async def toggle_is_active(self, company: Company) -> Company:
        company.is_active = not company.is_active
        await self.session.flush()
        return company

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        filters: CompanyListFiltersDTO | None = None,
    ) -> tuple[list[Company], int]:
        statement = self._apply_filters(select(Company), filters).order_by(
            Company.created_at.desc(),
            Company.id.desc(),
        )
        count_statement = self._apply_filters(select(func.count(Company.id)), filters)

        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        result = await self.session.scalars(statement.offset(offset).limit(page_size))
        return list(result.all()), total_items

    async def search_by_name(
        self,
        page: int,
        page_size: int,
        query: str,
        filters: CompanyListFiltersDTO | None = None,
    ) -> tuple[list[Company], int]:
        search_filters = filters or CompanyListFiltersDTO()
        search_filters = CompanyListFiltersDTO(
            search=query,
            is_active=search_filters.is_active,
            plan=search_filters.plan,
            expired_only=search_filters.expired_only,
        )
        return await self.list_paginated(page=page, page_size=page_size, filters=search_filters)

    async def filter_companies(
        self,
        page: int,
        page_size: int,
        filters: CompanyListFiltersDTO,
    ) -> tuple[list[Company], int]:
        return await self.list_paginated(page=page, page_size=page_size, filters=filters)

    async def count_all(self) -> int:
        statement = select(func.count(Company.id))
        return int((await self.session.scalar(statement)) or 0)

    async def count_active(self) -> int:
        statement = select(func.count(Company.id)).where(Company.is_active.is_(True))
        return int((await self.session.scalar(statement)) or 0)

    async def count_inactive(self) -> int:
        statement = select(func.count(Company.id)).where(Company.is_active.is_(False))
        return int((await self.session.scalar(statement)) or 0)

    async def count_expired(self) -> int:
        now = datetime.now(timezone.utc)
        statement = select(func.count(Company.id)).where(
            Company.subscription_end.is_not(None),
            Company.subscription_end < now,
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_by_plan(self, plan: CompanyPlan) -> int:
        statement = select(func.count(Company.id)).where(Company.plan == plan)
        return int((await self.session.scalar(statement)) or 0)

    async def list_recent(self, limit: int = 5) -> list[Company]:
        statement = select(Company).order_by(Company.created_at.desc(), Company.id.desc()).limit(limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    def _apply_filters(
        self,
        statement: Select[tuple[Company]] | Select[tuple[int]],
        filters: CompanyListFiltersDTO | None,
    ) -> Select:
        if filters is None:
            return statement

        if filters.search:
            statement = statement.where(func.lower(Company.name).contains(filters.search.strip().lower()))

        if filters.is_active is not None:
            statement = statement.where(Company.is_active.is_(filters.is_active))

        if filters.plan is not None:
            statement = statement.where(Company.plan == filters.plan)

        if filters.expired_only:
            now = datetime.now(timezone.utc)
            statement = statement.where(
                Company.subscription_end.is_not(None),
                Company.subscription_end < now,
            )

        return statement
