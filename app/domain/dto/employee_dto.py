from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from app.domain.dto.branch_dto import BranchDTO
from app.domain.dto.department_dto import DepartmentDTO
from app.domain.dto.shift_dto import ShiftDTO

if TYPE_CHECKING:
    from app.db.models.employee import Employee


@dataclass(slots=True, frozen=True)
class EmployeeCreateDTO:
    full_name: str
    phone: str | None = None
    telegram_id: int | None = None
    employee_code: str | None = None
    position: str | None = None
    branch_id: int | None = None
    department_id: int | None = None
    shift_id: int | None = None
    hire_date: date | None = None
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class EmployeeUpdateDTO:
    full_name: str
    phone: str | None
    telegram_id: int | None
    employee_code: str | None
    position: str | None
    branch_id: int | None
    department_id: int | None
    shift_id: int | None
    hire_date: date | None
    is_active: bool


@dataclass(slots=True, frozen=True)
class EmployeeFiltersDTO:
    search: str | None = None
    is_active: bool | None = None
    branch_id: int | None = None
    department_id: int | None = None
    shift_id: int | None = None


@dataclass(slots=True, frozen=True)
class EmployeeDTO:
    id: int
    company_id: int
    full_name: str
    phone: str | None
    telegram_id: int | None
    employee_code: str | None
    position: str | None
    branch_id: int | None
    department_id: int | None
    shift_id: int | None
    hire_date: date | None
    is_active: bool

    @classmethod
    def from_model(cls, employee: Employee) -> "EmployeeDTO":
        return cls(
            id=employee.id,
            company_id=employee.company_id,
            full_name=employee.full_name,
            phone=employee.phone,
            telegram_id=employee.telegram_id,
            employee_code=employee.employee_code,
            position=employee.position,
            branch_id=employee.branch_id,
            department_id=employee.department_id,
            shift_id=employee.shift_id,
            hire_date=employee.hire_date,
            is_active=employee.is_active,
        )


@dataclass(slots=True, frozen=True)
class EmployeeDetailDTO:
    id: int
    company_id: int
    full_name: str
    phone: str | None
    telegram_id: int | None
    employee_code: str | None
    position: str | None
    branch: BranchDTO | None
    department: DepartmentDTO | None
    shift: ShiftDTO | None
    hire_date: date | None
    is_active: bool

    @classmethod
    def from_model(cls, employee: Employee) -> "EmployeeDetailDTO":
        return cls(
            id=employee.id,
            company_id=employee.company_id,
            full_name=employee.full_name,
            phone=employee.phone,
            telegram_id=employee.telegram_id,
            employee_code=employee.employee_code,
            position=employee.position,
            branch=BranchDTO.from_model(employee.branch) if employee.branch else None,
            department=DepartmentDTO.from_model(employee.department) if employee.department else None,
            shift=ShiftDTO.from_model(employee.shift) if employee.shift else None,
            hire_date=employee.hire_date,
            is_active=employee.is_active,
        )


@dataclass(slots=True, frozen=True)
class EmployeeListPageDTO:
    items: list[EmployeeDetailDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(slots=True, frozen=True)
class CompanyAdminStatisticsDTO:
    total_employees: int
    active_employees: int
    inactive_employees: int
    total_branches: int
    total_departments: int
    total_shifts: int


@dataclass(slots=True, frozen=True)
class EmployeeBranchLocationDTO:
    branch_id: int
    branch_name: str
    latitude: float | None
    longitude: float | None
    allowed_radius_meters: int | None
    is_location_strict: bool


@dataclass(slots=True, frozen=True)
class EmployeeLocationValidationContextDTO:
    employee: EmployeeDetailDTO
    branch_location: EmployeeBranchLocationDTO | None
    has_valid_location: bool
