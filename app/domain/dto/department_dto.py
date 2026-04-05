from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.department import Department


@dataclass(slots=True, frozen=True)
class DepartmentCreateDTO:
    name: str
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class DepartmentUpdateDTO:
    name: str
    is_active: bool


@dataclass(slots=True, frozen=True)
class DepartmentDTO:
    id: int
    company_id: int
    name: str
    is_active: bool

    @classmethod
    def from_model(cls, department: Department) -> "DepartmentDTO":
        return cls(
            id=department.id,
            company_id=department.company_id,
            name=department.name,
            is_active=department.is_active,
        )


@dataclass(slots=True, frozen=True)
class DepartmentListPageDTO:
    items: list[DepartmentDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int
