from __future__ import annotations

from types import SimpleNamespace

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply.employee import build_employee_keyboard
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.attendance_dto import AttendanceRecordDTO, AttendanceSessionDTO, AttendanceTodayStatusDTO
from app.domain.dto.employee_dto import EmployeeAccessDTO
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.enums.attendance_status import AttendanceStatus
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.services.attendance_service import AttendanceService
from app.services.auth_service import AuthService


def _format_dt(value) -> str:
    if value is None:
        return "-"
    return AttendanceService.to_app_tz(value).strftime("%Y-%m-%d %H:%M")


def _format_time(value) -> str:
    if value is None:
        return "-"
    return AttendanceService.to_app_tz(value).strftime("%H:%M")


def _attendance_subject(access_or_employee):
    if hasattr(access_or_employee, "employee"):
        return access_or_employee
    return SimpleNamespace(employee=access_or_employee)


def format_check_in_timing(language, access_or_employee, record: AttendanceRecordDTO) -> str | None:
    if record.check_in_time is None:
        return None

    subject = _attendance_subject(access_or_employee)
    state, minutes = AttendanceService.get_check_in_timing_state(
        subject,
        record.check_in_time,
        late_minutes=record.late_minutes,
    )
    check_in_time = _format_time(record.check_in_time)
    if state == "early":
        return t(
            language,
            uz=f"Kelish bahosi: Erta keldi ({check_in_time}, {minutes} daqiqa oldin)",
            ru=f"Оценка прихода: Пришел раньше ({check_in_time}, на {minutes} мин раньше)",
            en=f"Arrival note: Arrived early ({check_in_time}, {minutes} minutes early)",
        )
    if state == "late":
        return t(
            language,
            uz=f"Kelish bahosi: Kech keldi ({check_in_time}, {minutes} daqiqa kech)",
            ru=f"Оценка прихода: Опоздал ({check_in_time}, на {minutes} мин позже)",
            en=f"Arrival note: Arrived late ({check_in_time}, {minutes} minutes late)",
        )
    if state == "on_time":
        return t(
            language,
            uz=f"Kelish bahosi: O'z vaqtida keldi ({check_in_time})",
            ru=f"Оценка прихода: Пришел вовремя ({check_in_time})",
            en=f"Arrival note: Arrived on time ({check_in_time})",
        )
    return None


def format_check_out_timing(language, access_or_employee, record: AttendanceRecordDTO) -> str | None:
    if record.check_in_time is None or record.check_out_time is None:
        return None

    subject = _attendance_subject(access_or_employee)
    state, minutes = AttendanceService.get_check_out_timing_state(
        subject,
        record.check_in_time,
        record.check_out_time,
        early_leave_minutes=record.early_leave_minutes,
    )
    check_out_time = _format_time(record.check_out_time)
    if state == "early":
        return t(
            language,
            uz=f"Ketish bahosi: Erta ketdi ({check_out_time}, {minutes} daqiqa oldin)",
            ru=f"Оценка ухода: Ушел раньше ({check_out_time}, на {minutes} мин раньше)",
            en=f"Departure note: Left early ({check_out_time}, {minutes} minutes early)",
        )
    if state == "late":
        return t(
            language,
            uz=f"Ketish bahosi: Kech ketdi ({check_out_time}, {minutes} daqiqa kech)",
            ru=f"Оценка ухода: Ушел позже ({check_out_time}, на {minutes} мин позже)",
            en=f"Departure note: Left late ({check_out_time}, {minutes} minutes late)",
        )
    if state == "on_time":
        return t(
            language,
            uz=f"Ketish bahosi: O'z vaqtida ketdi ({check_out_time})",
            ru=f"Оценка ухода: Ушел вовремя ({check_out_time})",
            en=f"Departure note: Left on time ({check_out_time})",
        )
    return None


def format_attendance_event_feedback(
    language,
    access_or_employee,
    record: AttendanceRecordDTO,
    session_type: AttendanceSessionType,
) -> str | None:
    if session_type is AttendanceSessionType.CHECK_IN:
        return format_check_in_timing(language, access_or_employee, record)
    return format_check_out_timing(language, access_or_employee, record)


def format_attendance_status(language, status: AttendanceStatus) -> str:
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


def format_session_type(language, session_type: AttendanceSessionType) -> str:
    mapping = {
        AttendanceSessionType.CHECK_IN: t(language, uz="Kirish", ru="Приход", en="Check-in"),
        AttendanceSessionType.CHECK_OUT: t(language, uz="Chiqish", ru="Уход", en="Check-out"),
    }
    return mapping.get(session_type, session_type.value)


def format_session_status(language, status: AttendanceSessionStatus) -> str:
    mapping = {
        AttendanceSessionStatus.PENDING_LOCATION: t(language, uz="Joylashuv kutilmoqda", ru="Ожидается локация", en="Waiting for location"),
        AttendanceSessionStatus.PENDING_VIDEO: t(language, uz="Video note kutilmoqda", ru="Ожидается video note", en="Waiting for video note"),
        AttendanceSessionStatus.COMPLETED: t(language, uz="Tugallangan", ru="Завершено", en="Completed"),
        AttendanceSessionStatus.REJECTED: t(language, uz="Rad etilgan", ru="Отклонено", en="Rejected"),
        AttendanceSessionStatus.EXPIRED: t(language, uz="Muddati tugagan", ru="Срок истек", en="Expired"),
        AttendanceSessionStatus.CANCELLED: t(language, uz="Bekor qilingan", ru="Отменено", en="Cancelled"),
    }
    return mapping.get(status, status.value)


def format_open_session(language, session: AttendanceSessionDTO) -> str:
    lines = [
        t(language, uz="Ochiq attendance session", ru="Открытая attendance-сессия", en="Open attendance session"),
        t(
            language,
            uz=f"🔄 Turi: {format_session_type(language, session.session_type)}",
            ru=f"🔄 Тип: {format_session_type(language, session.session_type)}",
            en=f"🔄 Type: {format_session_type(language, session.session_type)}",
        ),
        t(
            language,
            uz=f"📌 Holati: {format_session_status(language, session.status)}",
            ru=f"📌 Статус: {format_session_status(language, session.status)}",
            en=f"📌 Status: {format_session_status(language, session.status)}",
        ),
        t(
            language,
            uz=f"⏳ Amal qilish muddati: {_format_dt(session.expires_at)}",
            ru=f"⏳ Действует до: {_format_dt(session.expires_at)}",
            en=f"⏳ Expires at: {_format_dt(session.expires_at)}",
        ),
    ]
    if session.challenge_code:
        lines.append(
            t(
                language,
                uz=f"🔐 Challenge code: {session.challenge_code}",
                ru=f"🔐 Challenge code: {session.challenge_code}",
                en=f"🔐 Challenge code: {session.challenge_code}",
            )
        )
    if session.distance_to_branch_m is not None:
        lines.append(
            t(
                language,
                uz=f"📏 Filialgacha masofa: {session.distance_to_branch_m} m",
                ru=f"📏 Расстояние до филиала: {session.distance_to_branch_m} м",
                en=f"📏 Distance to branch: {session.distance_to_branch_m} m",
            )
        )
    return "\n".join(lines)


def format_attendance_record_detail(language, record: AttendanceRecordDTO) -> str:
    return "\n".join(
        [
            t(language, uz=f"📅 Sana: {record.date.isoformat()}", ru=f"📅 Дата: {record.date.isoformat()}", en=f"📅 Date: {record.date.isoformat()}"),
            t(language, uz=f"📌 Holat: {format_attendance_status(language, record.status)}", ru=f"📌 Статус: {format_attendance_status(language, record.status)}", en=f"📌 Status: {format_attendance_status(language, record.status)}"),
            t(language, uz=f"🕘 Check-in: {_format_dt(record.check_in_time)}", ru=f"🕘 Check-in: {_format_dt(record.check_in_time)}", en=f"🕘 Check-in: {_format_dt(record.check_in_time)}"),
            t(language, uz=f"🏁 Check-out: {_format_dt(record.check_out_time)}", ru=f"🏁 Check-out: {_format_dt(record.check_out_time)}", en=f"🏁 Check-out: {_format_dt(record.check_out_time)}"),
            t(language, uz=f"⏱ Ishlangan daqiqa: {record.worked_minutes}", ru=f"⏱ Отработано минут: {record.worked_minutes}", en=f"⏱ Worked minutes: {record.worked_minutes}"),
            t(language, uz=f"⌛ Kechikish: {record.late_minutes}", ru=f"⌛ Опоздание: {record.late_minutes}", en=f"⌛ Late minutes: {record.late_minutes}"),
            t(language, uz=f"🚪 Erta ketish: {record.early_leave_minutes}", ru=f"🚪 Ранний уход: {record.early_leave_minutes}", en=f"🚪 Early leave minutes: {record.early_leave_minutes}"),
        ]
    )


def format_today_status(language, status: AttendanceTodayStatusDTO) -> str:
    branch_name = status.employee.branch.name if status.employee.branch else "-"
    shift_name = status.employee.shift.name if status.employee.shift else "-"
    lines = [
        t(language, uz="Bugungi holatingiz", ru="Ваш статус на сегодня", en="Your status for today"),
        t(language, uz=f"🏢 Kompaniya: {status.company_name}", ru=f"🏢 Компания: {status.company_name}", en=f"🏢 Company: {status.company_name}"),
        t(language, uz=f"🏬 Filial: {branch_name}", ru=f"🏬 Филиал: {branch_name}", en=f"🏬 Branch: {branch_name}"),
        t(language, uz=f"⏰ Smena: {shift_name}", ru=f"⏰ Смена: {shift_name}", en=f"⏰ Shift: {shift_name}"),
    ]
    if status.attendance_record is None:
        lines.append(
            t(language, uz="Bugun hali attendance qaydi yo'q.", ru="Сегодня еще нет attendance-записи.", en="There is no attendance record for today yet.")
        )
    else:
        check_in_timing = format_check_in_timing(language, status.employee, status.attendance_record)
        check_out_timing = format_check_out_timing(language, status.employee, status.attendance_record)
        lines.extend(
            [
                t(language, uz=f"📌 Holat: {format_attendance_status(language, status.attendance_record.status)}", ru=f"📌 Статус: {format_attendance_status(language, status.attendance_record.status)}", en=f"📌 Status: {format_attendance_status(language, status.attendance_record.status)}"),
                t(language, uz=f"🕘 Check-in: {_format_dt(status.attendance_record.check_in_time)}", ru=f"🕘 Check-in: {_format_dt(status.attendance_record.check_in_time)}", en=f"🕘 Check-in: {_format_dt(status.attendance_record.check_in_time)}"),
                t(language, uz=f"🏁 Check-out: {_format_dt(status.attendance_record.check_out_time)}", ru=f"🏁 Check-out: {_format_dt(status.attendance_record.check_out_time)}", en=f"🏁 Check-out: {_format_dt(status.attendance_record.check_out_time)}"),
                t(language, uz=f"⌛ Kechikish: {status.attendance_record.late_minutes}", ru=f"⌛ Опоздание: {status.attendance_record.late_minutes}", en=f"⌛ Late minutes: {status.attendance_record.late_minutes}"),
                t(language, uz=f"🚪 Erta ketish: {status.attendance_record.early_leave_minutes}", ru=f"🚪 Ранний уход: {status.attendance_record.early_leave_minutes}", en=f"🚪 Early leave minutes: {status.attendance_record.early_leave_minutes}"),
                t(language, uz=f"⏱ Ishlangan daqiqa: {status.attendance_record.worked_minutes}", ru=f"⏱ Отработано минут: {status.attendance_record.worked_minutes}", en=f"⏱ Worked minutes: {status.attendance_record.worked_minutes}"),
            ]
        )
        if check_in_timing:
            lines.append(check_in_timing)
        if check_out_timing:
            lines.append(check_out_timing)
    if status.open_session is not None:
        lines.extend(["", format_open_session(language, status.open_session)])
    return "\n".join(lines)


async def require_employee_message(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> EmployeeAccessDTO | None:
    if message.from_user is None:
        return None

    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_employee(message.from_user.id)
    except LanguageSelectionRequiredError:
        await message.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Avval /start buyrug'ini yuboring.",
                ru="Сначала отправьте команду /start.",
                en="Please send /start first.",
            )
        )
    except AccessDeniedError as exc:
        await message.answer(
            t(
                exc.language or DEFAULT_LANGUAGE,
                uz="Sizda employee paneliga kirish huquqi yo'q.",
                ru="У вас нет доступа к employee панели.",
                en="You do not have access to the employee panel.",
            )
        )
    return None


async def require_employee_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> EmployeeAccessDTO | None:
    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_employee(callback.from_user.id)
    except LanguageSelectionRequiredError:
        await callback.answer(
            t(
                DEFAULT_LANGUAGE,
                uz="Avval /start buyrug'ini yuboring.",
                ru="Сначала отправьте команду /start.",
                en="Please send /start first.",
            ),
            show_alert=True,
        )
    except AccessDeniedError as exc:
        await callback.answer(
            t(
                exc.language or DEFAULT_LANGUAGE,
                uz="Sizda employee paneliga kirish huquqi yo'q.",
                ru="У вас нет доступа к employee панели.",
                en="You do not have access to the employee panel.",
            ),
            show_alert=True,
        )
    return None


async def show_employee_panel(
    message: Message,
    access: EmployeeAccessDTO,
    session: AsyncSession,
) -> None:
    today_status = await AttendanceService(session).get_today_status(access)
    await message.answer(
        format_today_status(access.user.language or DEFAULT_LANGUAGE, today_status),
        reply_markup=build_employee_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )
