from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.branch_repo import BranchRepository
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.department_repo import DepartmentRepository
from app.db.repositories.employee_repo import EmployeeRepository
from app.db.repositories.shift_repo import ShiftRepository
from app.domain.dto.company_dto import (
    CompanyDTO,
    CompanyStatisticsDTO,
    PlanDistributionDTO,
    SuperAdminDashboardDTO,
)
from app.domain.dto.employee_dto import CompanyAdminStatisticsDTO
from app.domain.enums.company_plan import CompanyPlan


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.branch_repo = BranchRepository(session)
        self.department_repo = DepartmentRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.employee_repo = EmployeeRepository(session)

    async def get_company_statistics(self) -> CompanyStatisticsDTO:
        plan_distribution = await self._get_plan_distribution()
        total_companies = await self.company_repo.count_all()
        active_companies = await self.company_repo.count_active()
        inactive_companies = await self.company_repo.count_inactive()
        expired_companies = await self.company_repo.count_expired()
        companies_with_admin = await self.company_admin_repo.count_assigned_companies()
        companies_without_admin = await self.company_admin_repo.count_unassigned_companies()

        return CompanyStatisticsDTO(
            total_companies=total_companies,
            active_companies=active_companies,
            inactive_companies=inactive_companies,
            expired_companies=expired_companies,
            companies_with_admin=companies_with_admin,
            companies_without_admin=companies_without_admin,
            plan_distribution=plan_distribution,
        )

    async def get_super_admin_dashboard(self) -> SuperAdminDashboardDTO:
        statistics = await self.get_company_statistics()
        recent_companies = await self.company_repo.list_recent(limit=5)

        return SuperAdminDashboardDTO(
            total_companies=statistics.total_companies,
            active_companies=statistics.active_companies,
            inactive_companies=statistics.inactive_companies,
            expired_companies=statistics.expired_companies,
            companies_with_admin=statistics.companies_with_admin,
            companies_without_admin=statistics.companies_without_admin,
            recent_companies=[CompanyDTO.from_model(company) for company in recent_companies],
            plan_distribution=statistics.plan_distribution,
        )

    async def _get_plan_distribution(self) -> PlanDistributionDTO:
        free_count = await self.company_repo.count_by_plan(CompanyPlan.FREE)
        basic_count = await self.company_repo.count_by_plan(CompanyPlan.BASIC)
        pro_count = await self.company_repo.count_by_plan(CompanyPlan.PRO)

        return PlanDistributionDTO(
            free=free_count,
            basic=basic_count,
            pro=pro_count,
        )

    async def get_company_admin_statistics(self, company_id: int) -> CompanyAdminStatisticsDTO:
        total_employees = await self.employee_repo.count_total(company_id)
        active_employees = await self.employee_repo.count_active(company_id)
        inactive_employees = await self.employee_repo.count_inactive(company_id)
        total_branches = await self.branch_repo.count_by_company(company_id)
        total_departments = await self.department_repo.count_by_company(company_id)
        total_shifts = await self.shift_repo.count_by_company(company_id)

        return CompanyAdminStatisticsDTO(
            total_employees=total_employees,
            active_employees=active_employees,
            inactive_employees=inactive_employees,
            total_branches=total_branches,
            total_departments=total_departments,
            total_shifts=total_shifts,
        )
