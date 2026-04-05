from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attendance_record import AttendanceRecord
from app.domain.enums.attendance_status import AttendanceStatus


class AttendanceRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_today_for_employee(self, employee_id: int, target_date: date) -> AttendanceRecord | None:
        statement = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date == target_date,
        )
        return await self.session.scalar(statement)

    async def create(
        self,
        *,
        company_id: int,
        employee_id: int,
        target_date: date,
        status: AttendanceStatus = AttendanceStatus.PRESENT,
    ) -> AttendanceRecord:
        record = AttendanceRecord(
            company_id=company_id,
            employee_id=employee_id,
            date=target_date,
            status=status,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def update(self, record: AttendanceRecord) -> AttendanceRecord:
        await self.session.flush()
        return record

    async def list_history_paginated(
        self,
        employee_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[AttendanceRecord], int]:
        count_statement = select(func.count(AttendanceRecord.id)).where(AttendanceRecord.employee_id == employee_id)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result.all()), total_items

    async def get_by_id(self, employee_id: int, record_id: int) -> AttendanceRecord | None:
        statement = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.id == record_id,
        )
        return await self.session.scalar(statement)

    async def exists_check_in_today(self, employee_id: int, target_date: date) -> bool:
        record = await self.get_today_for_employee(employee_id, target_date)
        return record is not None and record.check_in_time is not None
