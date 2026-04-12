from __future__ import annotations

from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.branch_repo import BranchRepository
from app.db.repositories.employee_repo import EmployeeRepository
from app.domain.dto.branch_dto import BranchCreateDTO, BranchDTO, BranchListPageDTO, BranchUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidRadiusError,
)


class BranchService:
    DEFAULT_PAGE_SIZE = 5
    DEFAULT_ALLOWED_RADIUS_METERS = 200

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.branch_repo = BranchRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.split()).strip()

    @staticmethod
    def normalize_optional_text(value: str) -> str | None:
        normalized = " ".join(value.split()).strip()
        return normalized or None

    @staticmethod
    def parse_optional_latitude(value: str) -> float | None:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        try:
            latitude = float(normalized)
        except ValueError as exc:
            raise InvalidLatitudeError() from exc
        if latitude < -90 or latitude > 90:
            raise InvalidLatitudeError()
        return latitude

    @staticmethod
    def parse_optional_longitude(value: str) -> float | None:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        try:
            longitude = float(normalized)
        except ValueError as exc:
            raise InvalidLongitudeError() from exc
        if longitude < -180 or longitude > 180:
            raise InvalidLongitudeError()
        return longitude

    @staticmethod
    def parse_shared_location(latitude: float, longitude: float) -> tuple[float, float]:
        if latitude < -90 or latitude > 90:
            raise InvalidLatitudeError()
        if longitude < -180 or longitude > 180:
            raise InvalidLongitudeError()
        return float(latitude), float(longitude)

    @staticmethod
    def parse_optional_radius(value: str) -> int | None:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        if not normalized.isdigit():
            raise InvalidRadiusError()
        radius = int(normalized)
        if radius <= 0:
            raise InvalidRadiusError()
        return radius

    @staticmethod
    def validate_location_fields(
        latitude: float | None,
        longitude: float | None,
        radius: int | None,
    ) -> None:
        if (latitude is None) != (longitude is None):
            if latitude is None:
                raise InvalidLatitudeError()
            raise InvalidLongitudeError()
        if latitude is None and longitude is None and radius is not None:
            raise InvalidRadiusError()

    @classmethod
    def normalize_location_fields(
        cls,
        latitude: float | None,
        longitude: float | None,
        radius: int | None,
    ) -> tuple[float | None, float | None, int | None]:
        cls.validate_location_fields(latitude, longitude, radius)
        if latitude is None and longitude is None:
            return None, None, None
        return latitude, longitude, radius or cls.DEFAULT_ALLOWED_RADIUS_METERS

    async def create_branch(
        self,
        company_id: int,
        payload: BranchCreateDTO,
        actor_telegram_id: int | None = None,
    ) -> BranchDTO:
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise BranchAlreadyExistsError("")

        await self.ensure_name_available(company_id, normalized_name)
        latitude, longitude, radius = self.normalize_location_fields(
            payload.latitude,
            payload.longitude,
            payload.allowed_radius_meters,
        )

        branch = await self.branch_repo.create(
            company_id,
            BranchCreateDTO(
                name=normalized_name,
                address=self.normalize_optional_text(payload.address or ""),
                latitude=latitude,
                longitude=longitude,
                allowed_radius_meters=radius,
                is_location_strict=payload.is_location_strict,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="branch_created",
            entity_type="branch",
            entity_id=branch.id,
            metadata_json={
                "company_id": company_id,
                "name": branch.name,
                "is_active": branch.is_active,
            },
        )
        await self.session.commit()
        return BranchDTO.from_model(branch)

    async def update_branch(
        self,
        company_id: int,
        branch_id: int,
        payload: BranchUpdateDTO,
        actor_telegram_id: int | None = None,
    ) -> BranchDTO:
        branch = await self._get_branch_or_raise(company_id, branch_id)
        normalized_name = self.normalize_name(payload.name)
        if not normalized_name:
            raise BranchAlreadyExistsError("")

        await self.ensure_name_available(company_id, normalized_name, exclude_branch_id=branch.id)
        latitude, longitude, radius = self.normalize_location_fields(
            payload.latitude,
            payload.longitude,
            payload.allowed_radius_meters,
        )

        updated_branch = await self.branch_repo.update(
            branch,
            BranchUpdateDTO(
                name=normalized_name,
                address=self.normalize_optional_text(payload.address or ""),
                latitude=latitude,
                longitude=longitude,
                allowed_radius_meters=radius,
                is_location_strict=payload.is_location_strict,
                is_active=payload.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="branch_updated",
            entity_type="branch",
            entity_id=updated_branch.id,
            metadata_json={
                "company_id": company_id,
                "name": updated_branch.name,
                "is_active": updated_branch.is_active,
            },
        )
        await self.session.commit()
        return BranchDTO.from_model(updated_branch)

    async def toggle_branch_status(
        self,
        company_id: int,
        branch_id: int,
        actor_telegram_id: int | None = None,
    ) -> BranchDTO:
        branch = await self._get_branch_or_raise(company_id, branch_id)
        updated_branch = await self.branch_repo.update(
            branch,
            BranchUpdateDTO(
                name=branch.name,
                address=branch.address,
                latitude=branch.latitude,
                longitude=branch.longitude,
                allowed_radius_meters=branch.allowed_radius_meters,
                is_location_strict=branch.is_location_strict,
                is_active=not branch.is_active,
            ),
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="branch_status_toggled",
            entity_type="branch",
            entity_id=updated_branch.id,
            metadata_json={"company_id": company_id, "is_active": updated_branch.is_active},
        )
        await self.session.commit()
        return BranchDTO.from_model(updated_branch)

    async def delete_branch(
        self,
        company_id: int,
        branch_id: int,
        actor_telegram_id: int | None = None,
    ) -> int:
        branch = await self._get_branch_or_raise(company_id, branch_id)
        detached_employees = await self.employee_repo.clear_branch_assignments(company_id, branch_id)

        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="branch_deleted",
            entity_type="branch",
            entity_id=branch.id,
            metadata_json={
                "company_id": company_id,
                "name": branch.name,
                "detached_employees": detached_employees,
            },
        )
        await self.branch_repo.delete(branch)
        await self.session.commit()
        return detached_employees

    async def get_branch(self, company_id: int, branch_id: int) -> BranchDTO:
        branch = await self._get_branch_or_raise(company_id, branch_id)
        return BranchDTO.from_model(branch)

    async def list_branches(
        self,
        company_id: int,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> BranchListPageDTO:
        safe_page_size = max(1, page_size)
        branches, total_items = await self.branch_repo.list_paginated(company_id, page, safe_page_size)
        total_pages = max(1, ceil(total_items / safe_page_size)) if total_items else 1
        normalized_page = min(max(page, 1), total_pages)
        if normalized_page != page and total_items:
            branches, total_items = await self.branch_repo.list_paginated(company_id, normalized_page, safe_page_size)
        return BranchListPageDTO(
            items=[BranchDTO.from_model(branch) for branch in branches],
            page=normalized_page,
            page_size=safe_page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def list_branch_options(self, company_id: int, *, active_only: bool = False) -> list[BranchDTO]:
        branches = await self.branch_repo.list_by_company(company_id, active_only=active_only)
        return [BranchDTO.from_model(branch) for branch in branches]

    async def ensure_name_available(
        self,
        company_id: int,
        name: str,
        exclude_branch_id: int | None = None,
    ) -> None:
        existing_branch = await self.branch_repo.get_by_name_in_company(company_id, name)
        if existing_branch is None:
            return
        if exclude_branch_id is not None and existing_branch.id == exclude_branch_id:
            return
        raise BranchAlreadyExistsError(name)

    async def _get_branch_or_raise(self, company_id: int, branch_id: int):
        branch = await self.branch_repo.get_by_id(company_id, branch_id)
        if branch is None:
            raise BranchNotFoundError(branch_id)
        return branch
