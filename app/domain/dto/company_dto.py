from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.domain.dto.user_dto import UserDTO
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.role import UserRole

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.company_admin_invite import CompanyAdminInvite


@dataclass(slots=True, frozen=True)
class CompanyCreateDTO:
    name: str
    plan: CompanyPlan = CompanyPlan.BASIC
    is_active: bool = True
    subscription_end: datetime | None = None


@dataclass(slots=True, frozen=True)
class CompanyUpdateDTO:
    name: str | None = None
    plan: CompanyPlan | None = None
    is_active: bool | None = None
    subscription_end: datetime | None = None
    subscription_end_provided: bool = False


@dataclass(slots=True, frozen=True)
class SubscriptionUpdateDTO:
    subscription_end: datetime | None


@dataclass(slots=True, frozen=True)
class CompanyAdminAssignDTO:
    company_id: int
    telegram_id: int
    role: UserRole = UserRole.COMPANY_ADMIN
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class CompanyDTO:
    id: int
    name: str
    plan: CompanyPlan
    is_active: bool
    subscription_end: datetime | None

    @classmethod
    def from_model(cls, company: Company) -> "CompanyDTO":
        return cls(
            id=company.id,
            name=company.name,
            plan=company.plan,
            is_active=company.is_active,
            subscription_end=company.subscription_end,
        )


@dataclass(slots=True, frozen=True)
class CompanyDetailDTO:
    id: int
    name: str
    plan: CompanyPlan
    is_active: bool
    subscription_end: datetime | None
    assigned_admin_telegram_id: int | None
    has_admin_assignment: bool
    admin_assignment_is_active: bool | None

    @classmethod
    def from_model(
        cls,
        company: Company,
        invite: CompanyAdminInvite | None = None,
    ) -> "CompanyDetailDTO":
        return cls(
            id=company.id,
            name=company.name,
            plan=company.plan,
            is_active=company.is_active,
            subscription_end=company.subscription_end,
            assigned_admin_telegram_id=invite.telegram_id if invite else None,
            has_admin_assignment=invite is not None,
            admin_assignment_is_active=invite.is_active if invite else None,
        )


@dataclass(slots=True, frozen=True)
class CompanyListPageDTO:
    items: list[CompanyDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(slots=True, frozen=True)
class CompanyListFiltersDTO:
    search: str | None = None
    is_active: bool | None = None
    plan: CompanyPlan | None = None
    expired_only: bool = False


@dataclass(slots=True, frozen=True)
class PlanDistributionDTO:
    free: int
    basic: int
    pro: int


@dataclass(slots=True, frozen=True)
class CompanyStatisticsDTO:
    total_companies: int
    active_companies: int
    inactive_companies: int
    expired_companies: int
    companies_with_admin: int
    companies_without_admin: int
    plan_distribution: PlanDistributionDTO


@dataclass(slots=True, frozen=True)
class SuperAdminDashboardDTO:
    total_companies: int
    active_companies: int
    inactive_companies: int
    expired_companies: int
    companies_with_admin: int
    companies_without_admin: int
    recent_companies: list[CompanyDTO]
    plan_distribution: PlanDistributionDTO


@dataclass(slots=True, frozen=True)
class CompanyAdminAccessDTO:
    user: UserDTO
    company: CompanyDTO
