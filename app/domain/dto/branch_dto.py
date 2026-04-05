from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.branch import Branch


@dataclass(slots=True, frozen=True)
class BranchCreateDTO:
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    allowed_radius_meters: int | None = None
    is_location_strict: bool = True
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class BranchUpdateDTO:
    name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    allowed_radius_meters: int | None
    is_location_strict: bool
    is_active: bool


@dataclass(slots=True, frozen=True)
class BranchDTO:
    id: int
    company_id: int
    name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    allowed_radius_meters: int | None
    is_location_strict: bool
    is_active: bool

    @classmethod
    def from_model(cls, branch: Branch) -> "BranchDTO":
        return cls(
            id=branch.id,
            company_id=branch.company_id,
            name=branch.name,
            address=branch.address,
            latitude=branch.latitude,
            longitude=branch.longitude,
            allowed_radius_meters=branch.allowed_radius_meters,
            is_location_strict=branch.is_location_strict,
            is_active=branch.is_active,
        )


@dataclass(slots=True, frozen=True)
class BranchListPageDTO:
    items: list[BranchDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int
