from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import Department
from app.domain.dto.department_dto import DepartmentCreateDTO, DepartmentUpdateDTO


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company_id: int, payload: DepartmentCreateDTO) -> Department:
        department = Department(
            company_id=company_id,
            name=payload.name,
            is_active=payload.is_active,
        )
        self.session.add(department)
        await self.session.flush()
        return department

    async def get_by_id(self, company_id: int, department_id: int) -> Department | None:
        statement = select(Department).where(
            Department.company_id == company_id,
            Department.id == department_id,
        )
        return await self.session.scalar(statement)

    async def get_by_name_in_company(self, company_id: int, name: str) -> Department | None:
        statement = select(Department).where(
            Department.company_id == company_id,
            func.lower(Department.name) == name.strip().lower(),
        )
        return await self.session.scalar(statement)

    async def list_paginated(
        self,
        company_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[Department], int]:
        count_statement = select(func.count(Department.id)).where(Department.company_id == company_id)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            select(Department)
            .where(Department.company_id == company_id)
            .order_by(Department.created_at.desc(), Department.id.desc())
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
    ) -> list[Department]:
        statement = select(Department).where(Department.company_id == company_id)
        if active_only:
            statement = statement.where(Department.is_active.is_(True))
        statement = statement.order_by(Department.name.asc(), Department.id.asc())
        result = await self.session.scalars(statement)
        return list(result.all())

    async def update(self, department: Department, payload: DepartmentUpdateDTO) -> Department:
        department.name = payload.name
        department.is_active = payload.is_active
        await self.session.flush()
        return department

    async def delete(self, department: Department) -> None:
        await self.session.delete(department)
        await self.session.flush()

    async def count_by_company(self, company_id: int) -> int:
        statement = select(func.count(Department.id)).where(Department.company_id == company_id)
        return int((await self.session.scalar(statement)) or 0)
