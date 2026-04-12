from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localization import DEFAULT_LANGUAGE, t
from app.db.repositories.company_admin_invite_repo import CompanyAdminInviteRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.attendance_dto import AttendanceRecordDTO, AttendanceSessionDTO
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.enums.attendance_status import AttendanceStatus
from app.services.attendance_service import AttendanceService


class AttendanceNotificationService:
    logger = logging.getLogger(__name__)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_admin_repo = CompanyAdminInviteRepository(session)
        self.user_repo = UserRepository(session)

    async def notify_company_admin_attendance(
        self,
        bot: Bot,
        *,
        access: EmployeeAccessDTO,
        attendance_session: AttendanceSessionDTO,
        attendance_record: AttendanceRecordDTO,
    ) -> bool:
        invite = await self.company_admin_repo.get_active_by_company_id(access.company.id)
        if invite is None:
            self.logger.info(
                "No active company admin assignment for company_id=%s while sending attendance notification",
                access.company.id,
            )
            return False

        admin_user = await self.user_repo.get_by_telegram_id(invite.telegram_id)
        language = (
            admin_user.language
            if admin_user is not None and admin_user.language is not None
            else DEFAULT_LANGUAGE
        )
        message_text = self._format_attendance_notification(
            language,
            access=access,
            attendance_session=attendance_session,
            attendance_record=attendance_record,
        )

        try:
            await bot.send_message(invite.telegram_id, message_text)
        except TelegramAPIError:
            self.logger.exception(
                "Failed to send attendance notification to company admin telegram_id=%s for company_id=%s employee_id=%s session_id=%s",
                invite.telegram_id,
                access.company.id,
                access.employee.id,
                attendance_session.id,
            )
            return False

        self.logger.info(
            "Attendance notification sent to company admin telegram_id=%s for company_id=%s employee_id=%s session_id=%s",
            invite.telegram_id,
            access.company.id,
            access.employee.id,
            attendance_session.id,
        )
        return True

    def _format_attendance_notification(
        self,
        language,
        *,
        access: EmployeeAccessDTO,
        attendance_session: AttendanceSessionDTO,
        attendance_record: AttendanceRecordDTO,
    ) -> str:
        session_type_label = self._session_type_label(language, attendance_session.session_type)
        status_label = self._attendance_status_label(language, attendance_record.status)
        branch_name = access.employee.branch.name if access.employee.branch is not None else "-"
        shift_name = access.employee.shift.name if access.employee.shift is not None else "-"
        shift_window = self._format_shift_window(access)
        event_time = attendance_session.completed_at or attendance_record.updated_at
        distance = (
            f"{attendance_session.distance_to_branch_m} m"
            if attendance_session.distance_to_branch_m is not None
            else "-"
        )
        video_received = (
            t(language, uz="Qabul qilindi", ru="Получено", en="Received")
            if attendance_session.is_video_received
            else t(language, uz="Yo'q", ru="Нет", en="No")
        )
        event_timing_note = self._event_timing_note(
            language,
            access=access,
            attendance_session=attendance_session,
            attendance_record=attendance_record,
        )

        lines = [
            t(
                language,
                uz=f"Ishchi {session_type_label} yakunladi",
                ru=f"Сотрудник завершил {session_type_label}",
                en=f"Employee completed {session_type_label}",
            ),
            t(language, uz=f"Kompaniya: {access.company.name}", ru=f"Компания: {access.company.name}", en=f"Company: {access.company.name}"),
            t(language, uz=f"Ishchi: {access.employee.full_name}", ru=f"Сотрудник: {access.employee.full_name}", en=f"Employee: {access.employee.full_name}"),
            t(language, uz=f"Employee code: {access.employee.employee_code or '-'}", ru=f"Employee code: {access.employee.employee_code or '-'}", en=f"Employee code: {access.employee.employee_code or '-'}"),
            t(language, uz=f"Telegram ID: {access.user.telegram_id}", ru=f"Telegram ID: {access.user.telegram_id}", en=f"Telegram ID: {access.user.telegram_id}"),
            t(language, uz=f"Filial: {branch_name}", ru=f"Филиал: {branch_name}", en=f"Branch: {branch_name}"),
            t(language, uz=f"Smena: {shift_name}", ru=f"Смена: {shift_name}", en=f"Shift: {shift_name}"),
            t(language, uz=f"Smena vaqti: {shift_window}", ru=f"Время смены: {shift_window}", en=f"Shift window: {shift_window}"),
            t(language, uz=f"Amal turi: {session_type_label}", ru=f"Тип действия: {session_type_label}", en=f"Event type: {session_type_label}"),
            t(language, uz=f"Amal vaqti: {self._format_datetime(event_time)}", ru=f"Время события: {self._format_datetime(event_time)}", en=f"Event time: {self._format_datetime(event_time)}"),
            t(language, uz=f"Filialgacha masofa: {distance}", ru=f"Дистанция до филиала: {distance}", en=f"Distance to branch: {distance}"),
            t(language, uz=f"Video note: {video_received}", ru=f"Video note: {video_received}", en=f"Video note: {video_received}"),
            t(language, uz=f"Attendance sanasi: {attendance_record.date.isoformat()}", ru=f"Дата attendance: {attendance_record.date.isoformat()}", en=f"Attendance date: {attendance_record.date.isoformat()}"),
            t(language, uz=f"Holat: {status_label}", ru=f"Статус: {status_label}", en=f"Status: {status_label}"),
            t(language, uz=f"Check-in: {self._format_datetime(attendance_record.check_in_time)}", ru=f"Check-in: {self._format_datetime(attendance_record.check_in_time)}", en=f"Check-in: {self._format_datetime(attendance_record.check_in_time)}"),
            t(language, uz=f"Check-out: {self._format_datetime(attendance_record.check_out_time)}", ru=f"Check-out: {self._format_datetime(attendance_record.check_out_time)}", en=f"Check-out: {self._format_datetime(attendance_record.check_out_time)}"),
            t(language, uz=f"Kechikish: {attendance_record.late_minutes} min", ru=f"Опоздание: {attendance_record.late_minutes} мин", en=f"Late: {attendance_record.late_minutes} min"),
            t(language, uz=f"Erta ketish: {attendance_record.early_leave_minutes} min", ru=f"Ранний уход: {attendance_record.early_leave_minutes} мин", en=f"Early leave: {attendance_record.early_leave_minutes} min"),
            t(language, uz=f"Ishlangan vaqt: {attendance_record.worked_minutes} min", ru=f"Отработано: {attendance_record.worked_minutes} мин", en=f"Worked: {attendance_record.worked_minutes} min"),
        ]
        if event_timing_note is not None:
            lines.append(event_timing_note)
        return "\n".join(lines)

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "-"
        return AttendanceService.to_app_tz(value).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_shift_window(access: EmployeeAccessDTO) -> str:
        shift = access.employee.shift
        if shift is None:
            return "-"
        return f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}"

    @staticmethod
    def _session_type_label(language, session_type: AttendanceSessionType) -> str:
        if session_type is AttendanceSessionType.CHECK_IN:
            return t(language, uz="check-in", ru="check-in", en="check-in")
        return t(language, uz="check-out", ru="check-out", en="check-out")

    @staticmethod
    def _attendance_status_label(language, status: AttendanceStatus) -> str:
        mapping = {
            AttendanceStatus.PRESENT: t(language, uz="Kelgan", ru="Присутствует", en="Present"),
            AttendanceStatus.LATE: t(language, uz="Kechikkan", ru="Опоздал", en="Late"),
            AttendanceStatus.ABSENT: t(language, uz="Yo'q", ru="Отсутствует", en="Absent"),
            AttendanceStatus.EARLY_LEAVE: t(language, uz="Erta ketgan", ru="Ушел раньше", en="Early leave"),
            AttendanceStatus.HALF_DAY: t(language, uz="Yarim kun", ru="Полдня", en="Half day"),
            AttendanceStatus.ON_LEAVE: t(language, uz="Ta'tilda", ru="В отпуске", en="On leave"),
            AttendanceStatus.SICK_LEAVE: t(language, uz="Kasallik ta'tili", ru="Больничный", en="Sick leave"),
            AttendanceStatus.WEEKEND: t(language, uz="Dam olish kuni", ru="Выходной", en="Weekend"),
        }
        return mapping.get(status, status.value)

    @staticmethod
    def _event_timing_note(
        language,
        *,
        access: EmployeeAccessDTO,
        attendance_session: AttendanceSessionDTO,
        attendance_record: AttendanceRecordDTO,
    ) -> str | None:
        if attendance_session.session_type is AttendanceSessionType.CHECK_IN:
            state, minutes = AttendanceService.get_check_in_timing_state(
                access,
                attendance_record.check_in_time,
                late_minutes=attendance_record.late_minutes,
            )
            if state == "early":
                return t(
                    language,
                    uz=f"Kelish bahosi: Erta keldi ({minutes} daqiqa oldin)",
                    ru=f"Оценка прихода: Пришел раньше (на {minutes} мин)",
                    en=f"Arrival note: Arrived early ({minutes} minutes early)",
                )
            if state == "late":
                return t(
                    language,
                    uz=f"Kelish bahosi: Kech keldi ({minutes} daqiqa kech)",
                    ru=f"Оценка прихода: Опоздал (на {minutes} мин)",
                    en=f"Arrival note: Arrived late ({minutes} minutes late)",
                )
            if state == "on_time":
                return t(
                    language,
                    uz="Kelish bahosi: O'z vaqtida keldi",
                    ru="Оценка прихода: Пришел вовремя",
                    en="Arrival note: Arrived on time",
                )
            return None

        state, minutes = AttendanceService.get_check_out_timing_state(
            access,
            attendance_record.check_in_time,
            attendance_record.check_out_time,
            early_leave_minutes=attendance_record.early_leave_minutes,
        )
        if state == "early":
            return t(
                language,
                uz=f"Ketish bahosi: Erta ketdi ({minutes} daqiqa oldin)",
                ru=f"Оценка ухода: Ушел раньше (на {minutes} мин)",
                en=f"Departure note: Left early ({minutes} minutes early)",
            )
        if state == "late":
            return t(
                language,
                uz=f"Ketish bahosi: Kech ketdi ({minutes} daqiqa kech)",
                ru=f"Оценка ухода: Ушел позже (на {minutes} мин)",
                en=f"Departure note: Left late ({minutes} minutes late)",
            )
        if state == "on_time":
            return t(
                language,
                uz="Ketish bahosi: O'z vaqtida ketdi",
                ru="Оценка ухода: Ушел вовремя",
                en="Departure note: Left on time",
            )
        return None
