from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.employee_common import (
    format_open_session,
    format_today_status,
    require_employee_callback,
    require_employee_message,
    show_employee_panel,
)
from app.bot.keyboards.reply.employee import (
    build_employee_cancel_keyboard,
    build_employee_location_keyboard,
    cancel_button_texts,
    check_in_button_texts,
    check_out_button_texts,
    today_status_button_texts,
)
from app.bot.states.attendance_states import AttendanceSessionStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.attendance_dto import AttendanceSessionStartResultDTO
from app.domain.enums.attendance_session_status import AttendanceSessionStatus
from app.domain.enums.attendance_session_type import AttendanceSessionType
from app.domain.exceptions.attendance_exceptions import (
    AttendanceAlreadyCheckedInError,
    AttendanceAlreadyCheckedOutError,
    AttendanceCheckOutWithoutCheckInError,
    AttendanceSessionExpiredError,
    AttendanceSessionNotFoundError,
    BranchLocationNotConfiguredError,
    LocationVerificationFailedError,
)
from app.domain.exceptions.auth_exceptions import AccessDeniedError
from app.domain.exceptions.employee_exceptions import (
    EmployeeBranchNotAssignedError,
    EmployeeInactiveError,
    EmployeeShiftNotAssignedError,
)
from app.services.attendance_service import AttendanceService

router = Router(name="attendance")


def _session_type_label(language, session_type: AttendanceSessionType) -> str:
    if session_type is AttendanceSessionType.CHECK_IN:
        return t(language, uz="ishga kirish", ru="приход", en="check-in")
    return t(language, uz="ishdan chiqish", ru="уход", en="check-out")


def _attendance_error_text(language, error: Exception) -> str:
    if isinstance(error, AttendanceAlreadyCheckedInError):
        return t(language, uz="Bugun allaqachon check-in qilingansiz.", ru="Сегодня вы уже сделали check-in.", en="You have already checked in today.")
    if isinstance(error, AttendanceAlreadyCheckedOutError):
        return t(language, uz="Bugun allaqachon check-out qilingansiz.", ru="Сегодня вы уже сделали check-out.", en="You have already checked out today.")
    if isinstance(error, AttendanceCheckOutWithoutCheckInError):
        return t(language, uz="Check-out qilishdan oldin check-in bo'lishi kerak.", ru="Перед check-out должен быть check-in.", en="You need a check-in before check-out.")
    if isinstance(error, EmployeeInactiveError):
        return t(language, uz="Sizning employee profilingiz nofaol.", ru="Ваш employee-профиль неактивен.", en="Your employee profile is inactive.")
    if isinstance(error, EmployeeBranchNotAssignedError):
        return t(language, uz="Sizga filial biriktirilmagan yoki u nofaol.", ru="Вам не назначен филиал или он неактивен.", en="No active branch is assigned to you.")
    if isinstance(error, EmployeeShiftNotAssignedError):
        return t(language, uz="Sizga smena biriktirilmagan yoki u nofaol.", ru="Вам не назначена смена или она неактивна.", en="No active shift is assigned to you.")
    if isinstance(error, BranchLocationNotConfiguredError):
        return t(language, uz="Filial lokatsiyasi sozlanmagan. Admin bilan bog'laning.", ru="Локация филиала не настроена. Свяжитесь с админом.", en="Branch location is not configured. Contact the admin.")
    if isinstance(error, AttendanceSessionExpiredError):
        return t(language, uz="Attendance session muddati tugagan. Qaytadan boshlang.", ru="Срок attendance-сессии истек. Начните заново.", en="The attendance session has expired. Please start again.")
    if isinstance(error, LocationVerificationFailedError):
        return t(language, uz="Siz filial radiusidan tashqaridasiz. Attendance rad etildi.", ru="Вы вне радиуса филиала. Attendance отклонен.", en="You are outside the branch radius. Attendance was rejected.")
    if isinstance(error, AttendanceSessionNotFoundError):
        return t(language, uz="Mos attendance session topilmadi.", ru="Подходящая attendance-сессия не найдена.", en="The matching attendance session was not found.")
    if isinstance(error, AccessDeniedError):
        return t(language, uz="Sizda bu amal uchun ruxsat yo'q.", ru="У вас нет доступа к этому действию.", en="You do not have access to this action.")
    return t(language, uz="Attendance amali bajarilmadi.", ru="Не удалось выполнить attendance-действие.", en="Could not complete the attendance action.")


async def _show_session_prompt(
    message: Message,
    state: FSMContext,
    result: AttendanceSessionStartResultDTO,
    language,
) -> None:
    session = result.session
    if session.status is AttendanceSessionStatus.PENDING_VIDEO:
        await state.set_state(AttendanceSessionStates.waiting_for_video)
        await message.answer(
            "\n".join(
                [
                    t(
                        language,
                        uz="Ochiq session davom ettiriladi. Endi dumaloq video yuboring.",
                        ru="Открытая сессия продолжается. Теперь отправьте video note.",
                        en="The open session will continue. Now send the video note.",
                    )
                    if result.resumed
                    else t(
                        language,
                        uz="Joylashuv tasdiqlandi. Endi dumaloq video yuboring.",
                        ru="Локация подтверждена. Теперь отправьте video note.",
                        en="Location verified. Now send the video note.",
                    ),
                    format_open_session(language, session),
                ]
            ),
            reply_markup=build_employee_cancel_keyboard(language),
        )
        return

    await state.set_state(AttendanceSessionStates.waiting_for_location)
    await message.answer(
        "\n".join(
            [
                t(
                    language,
                    uz=f"{_session_type_label(language, session.session_type).capitalize()} session boshlandi. Joylashuvingizni yuboring.",
                    ru=f"Сессия {_session_type_label(language, session.session_type)} началась. Отправьте свою локацию.",
                    en=f"The {_session_type_label(language, session.session_type)} session has started. Send your location.",
                )
                if not result.resumed
                else t(
                    language,
                    uz=f"Ochiq {_session_type_label(language, session.session_type)} session davom ettiriladi. Joylashuvingizni yuboring.",
                    ru=f"Открытая сессия {_session_type_label(language, session.session_type)} продолжается. Отправьте свою локацию.",
                    en=f"The open {_session_type_label(language, session.session_type)} session will continue. Send your location.",
                ),
                format_open_session(language, session),
            ]
        ),
        reply_markup=build_employee_location_keyboard(language),
    )


async def _restore_employee_panel_after_error(
    message: Message,
    access,
    session: AsyncSession,
) -> None:
    await show_employee_panel(message, access, session)


@router.message(LocalizedTextFilter(*check_in_button_texts()))
async def employee_check_in_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    attendance_service = AttendanceService(session)
    try:
        result = await attendance_service.start_check_in(access)
    except Exception as exc:
        await message.answer(_attendance_error_text(access.user.language, exc))
        return

    await _show_session_prompt(message, state, result, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*check_out_button_texts()))
async def employee_check_out_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    attendance_service = AttendanceService(session)
    try:
        result = await attendance_service.start_check_out(access)
    except Exception as exc:
        await message.answer(_attendance_error_text(access.user.language, exc))
        return

    await _show_session_prompt(message, state, result, access.user.language or DEFAULT_LANGUAGE)


@router.message(LocalizedTextFilter(*today_status_button_texts()))
async def employee_today_status_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    today_status = await AttendanceService(session).get_today_status(access)
    await message.answer(format_today_status(access.user.language, today_status))


@router.message(LocalizedTextFilter(*cancel_button_texts()))
async def employee_cancel_open_session_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    attendance_service = AttendanceService(session)
    open_session = await attendance_service.get_open_session(access)
    if open_session is None:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Ochiq attendance session topilmadi.",
                ru="Открытая attendance-сессия не найдена.",
                en="No open attendance session was found.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    await attendance_service.cancel_open_session(access, open_session.id)
    await state.clear()
    await message.answer(
        t(
            access.user.language,
            uz="Attendance session bekor qilindi.",
            ru="Attendance-сессия отменена.",
            en="The attendance session was cancelled.",
        )
    )
    await _restore_employee_panel_after_error(message, access, session)


@router.message(F.location)
async def employee_location_submission_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None or message.location is None:
        return

    attendance_service = AttendanceService(session)
    open_session = await attendance_service.get_open_session(access)
    if open_session is None:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Joylashuvni yuborish uchun avval check-in yoki check-out boshlang.",
                ru="Чтобы отправить локацию, сначала начните check-in или check-out.",
                en="Start a check-in or check-out before sending your location.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    if open_session.status is AttendanceSessionStatus.PENDING_VIDEO:
        await state.set_state(AttendanceSessionStates.waiting_for_video)
        await message.answer(
            "\n".join(
                [
                    t(
                        access.user.language,
                        uz="Joylashuv allaqachon tasdiqlangan. Endi dumaloq video yuboring.",
                        ru="Локация уже подтверждена. Теперь отправьте video note.",
                        en="The location is already verified. Now send the video note.",
                    ),
                    format_open_session(access.user.language, open_session),
                ]
            ),
            reply_markup=build_employee_cancel_keyboard(access.user.language or DEFAULT_LANGUAGE),
        )
        return

    if open_session.status is not AttendanceSessionStatus.PENDING_LOCATION:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Joylashuv qabul qilinmadi. Attendance sessionni qaytadan boshlang.",
                ru="Локация не была принята. Запустите attendance заново.",
                en="The location was not accepted. Please start the attendance flow again.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    try:
        result = await attendance_service.submit_location(
            access,
            open_session.id,
            latitude=message.location.latitude,
            longitude=message.location.longitude,
            accuracy=getattr(message.location, "horizontal_accuracy", None),
        )
    except Exception as exc:
        await state.clear()
        await message.answer(_attendance_error_text(access.user.language, exc))
        await _restore_employee_panel_after_error(message, access, session)
        return

    await state.set_state(AttendanceSessionStates.waiting_for_video)
    await message.answer(
        "\n".join(
            [
                t(
                    access.user.language,
                    uz=f"Joylashuv tasdiqlandi. Masofa: {result.distance_to_branch_m} metr.",
                    ru=f"Локация подтверждена. Расстояние: {result.distance_to_branch_m} метров.",
                    en=f"Location verified. Distance: {result.distance_to_branch_m} meters.",
                ),
                t(
                    access.user.language,
                    uz=f"🔐 Challenge code: {result.challenge_code}",
                    ru=f"🔐 Challenge code: {result.challenge_code}",
                    en=f"🔐 Challenge code: {result.challenge_code}",
                ),
                t(
                    access.user.language,
                    uz="Endi dumaloq video yuboring. Iloji bo'lsa challenge code ni ayting.",
                    ru="Теперь отправьте video note. По возможности произнесите challenge code.",
                    en="Now send a video note. If possible, say the challenge code.",
                ),
            ]
        ),
        reply_markup=build_employee_cancel_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.message(AttendanceSessionStates.waiting_for_location)
async def employee_waiting_location_fallback_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    attendance_service = AttendanceService(session)
    open_session = await attendance_service.get_open_session(access)
    if open_session is None:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Ochiq attendance session topilmadi. Qaytadan boshlang.",
                ru="Открытая attendance-сессия не найдена. Начните заново.",
                en="No open attendance session was found. Please start again.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    if open_session.status is AttendanceSessionStatus.PENDING_VIDEO:
        await state.set_state(AttendanceSessionStates.waiting_for_video)
        await message.answer(
            "\n".join(
                [
                    t(
                        access.user.language,
                        uz="Joylashuv bosqichi allaqachon tugagan. Endi dumaloq video yuboring.",
                        ru="Этап локации уже завершен. Теперь отправьте video note.",
                        en="The location step is already complete. Now send the video note.",
                    ),
                    format_open_session(access.user.language, open_session),
                ]
            ),
            reply_markup=build_employee_cancel_keyboard(access.user.language or DEFAULT_LANGUAGE),
        )
        return

    if open_session.status is not AttendanceSessionStatus.PENDING_LOCATION:
        return

    await message.answer(
        "\n".join(
            [
                t(
                    access.user.language,
                    uz="Joylashuv hali olinmadi. Telegramdagi joylashuv yuborish tugmasidan foydalaning.",
                    ru="Локация еще не получена. Используйте кнопку отправки геолокации в Telegram.",
                    en="The location has not been received yet. Use the Telegram location share button.",
                ),
                format_open_session(access.user.language, open_session),
            ]
        ),
        reply_markup=build_employee_location_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.message(F.video_note)
async def employee_video_note_submission_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None or message.video_note is None:
        return

    attendance_service = AttendanceService(session)
    open_session = await attendance_service.get_open_session(access)
    if open_session is None:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Avval joylashuvni tasdiqlang, so'ng dumaloq video yuboring.",
                ru="Сначала подтвердите локацию, затем отправьте video note.",
                en="Verify the location first, then send the video note.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    if open_session.status is AttendanceSessionStatus.PENDING_LOCATION:
        await state.set_state(AttendanceSessionStates.waiting_for_location)
        await message.answer(
            "\n".join(
                [
                    t(
                        access.user.language,
                        uz="Avval joylashuvingiz yuborilishi kerak. So'ng video note yuborasiz.",
                        ru="Сначала нужно отправить геолокацию. Затем уже video note.",
                        en="You need to send your location first. After that, send the video note.",
                    ),
                    format_open_session(access.user.language, open_session),
                ]
            ),
            reply_markup=build_employee_location_keyboard(access.user.language or DEFAULT_LANGUAGE),
        )
        return

    if open_session.status is not AttendanceSessionStatus.PENDING_VIDEO:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Video note qabul qilinmadi. Attendance sessionni qaytadan boshlang.",
                ru="Video note не был принят. Запустите attendance заново.",
                en="The video note was not accepted. Please start the attendance flow again.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    try:
        completed_session, _record = await attendance_service.submit_video_note(
            access,
            open_session.id,
            file_id=message.video_note.file_id,
            file_unique_id=message.video_note.file_unique_id,
        )
        today_status = await attendance_service.get_today_status(access)
    except Exception as exc:
        await state.clear()
        await message.answer(_attendance_error_text(access.user.language, exc))
        await _restore_employee_panel_after_error(message, access, session)
        return

    await state.clear()
    await message.answer(
        "\n".join(
            [
                t(
                    access.user.language,
                    uz=f"{_session_type_label(access.user.language, completed_session.session_type).capitalize()} muvaffaqiyatli yakunlandi.",
                    ru=f"{_session_type_label(access.user.language, completed_session.session_type).capitalize()} успешно завершен.",
                    en=f"{_session_type_label(access.user.language, completed_session.session_type).capitalize()} completed successfully.",
                ),
                format_today_status(access.user.language, today_status),
            ]
        )
    )


@router.message(AttendanceSessionStates.waiting_for_video)
async def employee_waiting_video_fallback_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    attendance_service = AttendanceService(session)
    open_session = await attendance_service.get_open_session(access)
    if open_session is None:
        await state.clear()
        await message.answer(
            t(
                access.user.language,
                uz="Ochiq attendance session topilmadi. Qaytadan boshlang.",
                ru="Открытая attendance-сессия не найдена. Начните заново.",
                en="No open attendance session was found. Please start again.",
            )
        )
        await _restore_employee_panel_after_error(message, access, session)
        return

    if open_session.status is AttendanceSessionStatus.PENDING_LOCATION:
        await state.set_state(AttendanceSessionStates.waiting_for_location)
        await message.answer(
            "\n".join(
                [
                    t(
                        access.user.language,
                        uz="Avval joylashuv yuboring. Video note keyin yuboriladi.",
                        ru="Сначала отправьте геолокацию. Video note отправляется после этого.",
                        en="Send the location first. The video note comes after that.",
                    ),
                    format_open_session(access.user.language, open_session),
                ]
            ),
            reply_markup=build_employee_location_keyboard(access.user.language or DEFAULT_LANGUAGE),
        )
        return

    if open_session.status is not AttendanceSessionStatus.PENDING_VIDEO:
        return

    await message.answer(
        "\n".join(
            [
                t(
                    access.user.language,
                    uz="Endi dumaloq video yuborilishi kerak. Oddiy matn yoki boshqa fayl qabul qilinmaydi.",
                    ru="Теперь нужно отправить video note. Обычный текст или другой файл не подходят.",
                    en="Now you need to send a video note. Plain text or another file type will not work.",
                ),
                format_open_session(access.user.language, open_session),
            ]
        ),
        reply_markup=build_employee_cancel_keyboard(access.user.language or DEFAULT_LANGUAGE),
    )


@router.callback_query(F.data.startswith("attendance:cancel:"))
async def employee_cancel_session_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.data is None or callback.message is None:
        return

    session_id = int(callback.data.rsplit(":", 1)[-1])
    attendance_service = AttendanceService(session)
    try:
        await attendance_service.cancel_open_session(access, session_id)
    except Exception as exc:
        await callback.answer(_attendance_error_text(access.user.language, exc), show_alert=True)
        return

    await state.clear()
    await callback.answer(
        t(
            access.user.language,
            uz="Attendance session bekor qilindi.",
            ru="Attendance-сессия отменена.",
            en="Attendance session cancelled.",
        )
    )
    await callback.message.edit_text(
        t(
            access.user.language,
            uz="Attendance session bekor qilindi.",
            ru="Attendance-сессия отменена.",
            en="Attendance session cancelled.",
        )
    )


@router.callback_query(F.data == "attendance:history:noop")
async def attendance_history_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()
