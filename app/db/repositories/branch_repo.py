from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.branch import Branch
from app.domain.dto.branch_dto import BranchCreateDTO, BranchUpdateDTO


class BranchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company_id: int, payload: BranchCreateDTO) -> Branch:
        branch = Branch(
            company_id=company_id,
            name=payload.name,
            address=payload.address,
            latitude=payload.latitude,
            longitude=payload.longitude,
            allowed_radius_meters=payload.allowed_radius_meters,
            is_location_strict=payload.is_location_strict,
            is_active=payload.is_active,
        )
        self.session.add(branch)
        await self.session.flush()
        return branch

    async def get_by_id(self, company_id: int, branch_id: int) -> Branch | None:
        statement = select(Branch).where(
            Branch.company_id == company_id,
            Branch.id == branch_id,
        )
        return await self.session.scalar(statement)

    async def get_by_name_in_company(self, company_id: int, name: str) -> Branch | None:
        statement = select(Branch).where(
            Branch.company_id == company_id,
            func.lower(Branch.name) == name.strip().lower(),
        )
        return await self.session.scalar(statement)

    async def list_paginated(
        self,
        company_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[Branch], int]:
        count_statement = select(func.count(Branch.id)).where(Branch.company_id == company_id)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            select(Branch)
            .where(Branch.company_id == company_id)
            .order_by(Branch.created_at.desc(), Branch.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result.all()), total_items

    async def list_by_company(
        self,
        company_id: int,
        *,
        active_only: bool = False,
    ) -> list[Branch]:
        statement = select(Branch).where(Branch.company_id == company_id)
        if active_only:
            statement = statement.where(Branch.is_active.is_(True))
        statement = statement.order_by(Branch.name.asc(), Branch.id.asc())
        result = await self.session.scalars(statement)
        return list(result.all())

    async def update(self, branch: Branch, payload: BranchUpdateDTO) -> Branch:
        branch.name = payload.name
        branch.address = payload.address
        branch.latitude = payload.latitude
        branch.longitude = payload.longitude
        branch.allowed_radius_meters = payload.allowed_radius_meters
        branch.is_location_strict = payload.is_location_strict
        branch.is_active = payload.is_active
        await self.session.flush()
        return branch

    async def delete(self, branch: Branch) -> None:
        await self.session.delete(branch)
        await self.session.flush()

    async def count_by_company(self, company_id: int) -> int:
        statement = select(func.count(Branch.id)).where(Branch.company_id == company_id)
        return int((await self.session.scalar(statement)) or 0)
