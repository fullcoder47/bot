from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localization import DEFAULT_LANGUAGE, t
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.dto.leave_dto import LeaveRequestDTO
from app.domain.enums.leave_type import LeaveType


class LeaveNotificationService:
    logger = logging.getLogger(__name__)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.user_repo = UserRepository(session)

    async def notify_company_admin(
        self,
        bot: Bot,
        *,
        access: EmployeeAccessDTO,
        leave_request: LeaveRequestDTO,
    ) -> bool:
        invite = await self.company_admin_repo.get_active_by_company_id(access.company.id)
        if invite is None:
            self.logger.info(
                "Leave notification skipped because no active company admin exists for company_id=%s",
                access.company.id,
            )
            return False

        admin_user = await self.user_repo.get_by_telegram_id(invite.telegram_id)
        language = (
            admin_user.language
            if admin_user is not None and admin_user.language is not None
            else DEFAULT_LANGUAGE
        )
        message_text = self._format_leave_notification(language, access, leave_request)
        try:
            await bot.send_message(invite.telegram_id, message_text)
        except TelegramAPIError:
            self.logger.exception(
                "Failed to send leave notification to company admin telegram_id=%s for leave_request_id=%s",
                invite.telegram_id,
                leave_request.id,
            )
            return False

        self.logger.info(
            "Leave notification sent to company admin telegram_id=%s for leave_request_id=%s",
            invite.telegram_id,
            leave_request.id,
        )
        return True

    @staticmethod
    def _leave_type_label(language, leave_type: LeaveType) -> str:
        mapping = {
            LeaveType.VACATION: t(language, uz="Ta'til", ru="Отпуск", en="Vacation"),
            LeaveType.SICK: t(language, uz="Kasallik", ru="Больничный", en="Sick"),
            LeaveType.PERSONAL: t(language, uz="Shaxsiy", ru="Личное", en="Personal"),
        }
        return mapping.get(leave_type, leave_type.value)

    def _format_leave_notification(
        self,
        language,
        access: EmployeeAccessDTO,
        leave_request: LeaveRequestDTO,
    ) -> str:
        branch_name = access.employee.branch.name if access.employee.branch is not None else "-"
        department_name = access.employee.department.name if access.employee.department is not None else "-"
        return "\n".join(
            [
                t(language, uz="Yangi ta'til so'rovi", ru="Новый запрос на отпуск", en="New leave request"),
                t(language, uz=f"Kompaniya: {access.company.name}", ru=f"Компания: {access.company.name}", en=f"Company: {access.company.name}"),
                t(language, uz=f"Ishchi: {access.employee.full_name}", ru=f"Сотрудник: {access.employee.full_name}", en=f"Employee: {access.employee.full_name}"),
                t(language, uz=f"Employee code: {access.employee.employee_code or '-'}", ru=f"Employee code: {access.employee.employee_code or '-'}", en=f"Employee code: {access.employee.employee_code or '-'}"),
                t(language, uz=f"Filial: {branch_name}", ru=f"Филиал: {branch_name}", en=f"Branch: {branch_name}"),
                t(language, uz=f"Bo'lim: {department_name}", ru=f"Отдел: {department_name}", en=f"Department: {department_name}"),
                t(language, uz=f"Turi: {self._leave_type_label(language, leave_request.leave_type)}", ru=f"Тип: {self._leave_type_label(language, leave_request.leave_type)}", en=f"Type: {self._leave_type_label(language, leave_request.leave_type)}"),
                t(language, uz=f"Davr: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}", ru=f"Период: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}", en=f"Period: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}"),
                t(language, uz=f"Sabab: {leave_request.reason}", ru=f"Причина: {leave_request.reason}", en=f"Reason: {leave_request.reason}"),
                t(language, uz="Status: Kutilmoqda", ru="Статус: Ожидает", en="Status: Pending"),
            ]
        )
