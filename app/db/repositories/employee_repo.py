from __future__ import annotations

from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.employee import Employee
from app.domain.dto.employee_dto import EmployeeCreateDTO, EmployeeFiltersDTO, EmployeeUpdateDTO


class EmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company_id: int, payload: EmployeeCreateDTO) -> Employee:
        employee = Employee(
            company_id=company_id,
            full_name=payload.full_name,
            phone=payload.phone,
            telegram_id=payload.telegram_id,
            employee_code=payload.employee_code,
            position=payload.position,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            shift_id=payload.shift_id,
            hire_date=payload.hire_date,
            is_active=payload.is_active,
        )
        self.session.add(employee)
        await self.session.flush()
        return employee

    async def get_by_id(self, company_id: int, employee_id: int) -> Employee | None:
        statement = (
            select(Employee)
            .options(
                joinedload(Employee.company),
                joinedload(Employee.branch),
                joinedload(Employee.department),
                joinedload(Employee.shift),
            )
            .where(
                Employee.company_id == company_id,
                Employee.id == employee_id,
            )
        )
        return await self.session.scalar(statement)

    async def get_by_telegram_id(
        self,
        telegram_id: int,
        *,
        active_only: bool = False,
    ) -> Employee | None:
        statement = (
            select(Employee)
            .options(
                joinedload(Employee.company),
                joinedload(Employee.branch),
                joinedload(Employee.department),
                joinedload(Employee.shift),
            )
            .where(Employee.telegram_id == telegram_id)
            .order_by(Employee.created_at.desc(), Employee.id.desc())
        )
        if active_only:
            statement = statement.where(Employee.is_active.is_(True))
        return await self.session.scalar(statement)

    async def get_by_employee_code(self, company_id: int, employee_code: str) -> Employee | None:
        statement = select(Employee).where(
            Employee.company_id == company_id,
            func.lower(Employee.employee_code) == employee_code.strip().lower(),
        )
        return await self.session.scalar(statement)

    async def list_paginated(
        self,
        company_id: int,
        page: int,
        page_size: int,
        filters: EmployeeFiltersDTO | None = None,
    ) -> tuple[list[Employee], int]:
        base_statement = self._apply_filters(
            select(Employee).options(
                joinedload(Employee.branch),
                joinedload(Employee.department),
                joinedload(Employee.shift),
            ),
            company_id,
            filters,
        )
        count_statement = self._apply_filters(select(func.count(Employee.id)), company_id, filters)
        total_items = int((await self.session.scalar(count_statement)) or 0)
        offset = max(page - 1, 0) * page_size
        statement = (
            base_statement
            .order_by(Employee.created_at.desc(), Employee.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.scalars(statement)
        return list(result.unique().all()), total_items

    async def list_by_company(
        self,
        company_id: int,
        *,
        active_only: bool = False,
    ) -> list[Employee]:
        statement = (
            select(Employee)
            .options(
                joinedload(Employee.branch),
                joinedload(Employee.department),
                joinedload(Employee.shift),
            )
            .where(Employee.company_id == company_id)
        )
        if active_only:
            statement = statement.where(Employee.is_active.is_(True))
        statement = statement.order_by(Employee.full_name.asc(), Employee.id.asc())
        result = await self.session.scalars(statement)
        return list(result.unique().all())

    async def update(self, employee: Employee, payload: EmployeeUpdateDTO) -> Employee:
        employee.full_name = payload.full_name
        employee.phone = payload.phone
        employee.telegram_id = payload.telegram_id
        employee.employee_code = payload.employee_code
        employee.position = payload.position
        employee.branch_id = payload.branch_id
        employee.department_id = payload.department_id
        employee.shift_id = payload.shift_id
        employee.hire_date = payload.hire_date
        employee.is_active = payload.is_active
        await self.session.flush()
        return employee

    async def link_user(self, employee: Employee, user_id: int | None) -> Employee:
        employee.user_id = user_id
        await self.session.flush()
        return employee

    async def toggle_is_active(self, employee: Employee) -> Employee:
        employee.is_active = not employee.is_active
        await self.session.flush()
        return employee

    async def count_total(self, company_id: int) -> int:
        statement = select(func.count(Employee.id)).where(Employee.company_id == company_id)
        return int((await self.session.scalar(statement)) or 0)

    async def count_active(self, company_id: int) -> int:
        statement = select(func.count(Employee.id)).where(
            Employee.company_id == company_id,
            Employee.is_active.is_(True),
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_inactive(self, company_id: int) -> int:
        statement = select(func.count(Employee.id)).where(
            Employee.company_id == company_id,
            Employee.is_active.is_(False),
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_by_branch(self, company_id: int, branch_id: int) -> int:
        statement = select(func.count(Employee.id)).where(
            Employee.company_id == company_id,
            Employee.branch_id == branch_id,
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_by_department(self, company_id: int, department_id: int) -> int:
        statement = select(func.count(Employee.id)).where(
            Employee.company_id == company_id,
            Employee.department_id == department_id,
        )
        return int((await self.session.scalar(statement)) or 0)

    async def count_by_shift(self, company_id: int, shift_id: int) -> int:
        statement = select(func.count(Employee.id)).where(
            Employee.company_id == company_id,
            Employee.shift_id == shift_id,
        )
        return int((await self.session.scalar(statement)) or 0)

    async def clear_branch_assignments(self, company_id: int, branch_id: int) -> int:
        result = await self.session.execute(
            update(Employee)
            .where(
                Employee.company_id == company_id,
                Employee.branch_id == branch_id,
            )
            .values(branch_id=None)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def clear_department_assignments(self, company_id: int, department_id: int) -> int:
        result = await self.session.execute(
            update(Employee)
            .where(
                Employee.company_id == company_id,
                Employee.department_id == department_id,
            )
            .values(department_id=None)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def clear_shift_assignments(self, company_id: int, shift_id: int) -> int:
        result = await self.session.execute(
            update(Employee)
            .where(
                Employee.company_id == company_id,
                Employee.shift_id == shift_id,
            )
            .values(shift_id=None)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    def _apply_filters(self, statement, company_id: int, filters: EmployeeFiltersDTO | None):
        statement = statement.where(Employee.company_id == company_id)
        if filters is None:
            return statement

        if filters.search:
            query = filters.search.strip().lower()
            statement = statement.where(
                or_(
                    func.lower(Employee.full_name).contains(query),
                    func.lower(func.coalesce(Employee.employee_code, "")).contains(query),
                    cast(Employee.telegram_id, String).contains(query),
                )
            )

        if filters.is_active is not None:
            statement = statement.where(Employee.is_active.is_(filters.is_active))

        if filters.branch_id is not None:
            statement = statement.where(Employee.branch_id == filters.branch_id)

        if filters.department_id is not None:
            statement = statement.where(Employee.department_id == filters.department_id)

        if filters.shift_id is not None:
            statement = statement.where(Employee.shift_id == filters.shift_id)

        return statement
