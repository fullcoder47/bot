from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.company import Company
from app.db.models.company_admin_invite import CompanyAdminInvite
from app.domain.dto.company_dto import CompanyAdminAssignDTO


class CompanyAdminInviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_company_id(self, company_id: int) -> CompanyAdminInvite | None:
        statement = (
            select(CompanyAdminInvite)
            .options(joinedload(CompanyAdminInvite.company))
            .where(CompanyAdminInvite.company_id == company_id)
        )
        return await self.session.scalar(statement)

    async def get_active_by_telegram_id(self, telegram_id: int) -> CompanyAdminInvite | None:
        statement = (
            select(CompanyAdminInvite)
            .join(Company, Company.id == CompanyAdminInvite.company_id)
            .options(joinedload(CompanyAdminInvite.company))
            .where(
                CompanyAdminInvite.telegram_id == telegram_id,
                CompanyAdminInvite.is_active.is_(True),
                Company.is_active.is_(True),
            )
        )
        return await self.session.scalar(statement)

    async def upsert(self, payload: CompanyAdminAssignDTO) -> CompanyAdminInvite:
        invite = await self.get_by_company_id(payload.company_id)

        if invite is None:
            invite = CompanyAdminInvite(
                company_id=payload.company_id,
                telegram_id=payload.telegram_id,
                role=payload.role,
                is_active=payload.is_active,
            )
            self.session.add(invite)
        else:
            invite.telegram_id = payload.telegram_id
            invite.role = payload.role
            invite.is_active = payload.is_active

        await self.session.flush()
        return invite
