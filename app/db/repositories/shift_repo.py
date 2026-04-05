from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.shift import Shift
from app.domain.dto.shift_dto import ShiftCreateDTO, ShiftUpdateDTO


class ShiftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company_id: int, payload: ShiftCreateDTO) -> Shift:
        shift = Shift(
            company_id=company_id,
            name=payload.name,
            start_time=payload.start_time,
            end_time=payload.end_time,
            late_after_minutes=payload.late_after_minutes,
            early_leave_before_minutes=payload.early_leave_before_minutes,
            work_days=payload.work_days,
            is_active=payload.is_active,
        )
        self.session.add(shift)
        await self.session.flush()
        return shift

    async def get_by_id(self, company_id: int, shift_id: int) -> Shift | None:
        statement = select(Shift).where(
            Shift.company_id == company_id,
            Shift.id == shift_id,
        )
        return await self.session.scalar(statement)

    async def get_by_name_in_company(self, company_id: int, name: str) -> Shift | None:
        statement = select(Shift).where(
            Shift.company_id == company_id,
            func.lower(Shift.name) == name.strip().lower(),
        )
        return await self.session.scalar(statement)

    async def list_paginated(
        self,
        company_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[Shift], int]:
        count_statement = select(func.count(Shift.id)).where(Shift.company_id == company_id)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            select(Shift)
            .where(Shift.company_id == company_id)
            .order_by(Shift.created_at.desc(), Shift.id.desc())
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
    ) -> list[Shift]:
        statement = select(Shift).where(Shift.company_id == company_id)
        if active_only:
            statement = statement.where(Shift.is_active.is_(True))
        statement = statement.order_by(Shift.name.asc(), Shift.id.asc())
        result = await self.session.scalars(statement)
        return list(result.all())

    async def update(self, shift: Shift, payload: ShiftUpdateDTO) -> Shift:
        shift.name = payload.name
        shift.start_time = payload.start_time
        shift.end_time = payload.end_time
        shift.late_after_minutes = payload.late_after_minutes
        shift.early_leave_before_minutes = payload.early_leave_before_minutes
        shift.work_days = payload.work_days
        shift.is_active = payload.is_active
        await self.session.flush()
        return shift

    async def delete(self, shift: Shift) -> None:
        await self.session.delete(shift)
        await self.session.flush()

    async def count_by_company(self, company_id: int) -> int:
        statement = select(func.count(Shift.id)).where(Shift.company_id == company_id)
        return int((await self.session.scalar(statement)) or 0)
