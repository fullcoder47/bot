from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.employee_common import require_employee_callback, require_employee_message, show_employee_panel
from app.bot.keyboards.inline.attendance import build_leave_confirmation_keyboard, build_leave_type_keyboard
from app.bot.keyboards.reply.employee import build_employee_cancel_keyboard, cancel_button_texts, leave_request_button_texts
from app.bot.states.leave_states import LeaveRequestStates
from app.core.config import Settings
from app.core.localization import t
from app.domain.dto.leave_dto import LeaveRequestCreateDTO
from app.domain.enums.leave_type import LeaveType
from app.domain.exceptions.attendance_exceptions import LeaveRequestValidationError
from app.services.leave_notification_service import LeaveNotificationService
from app.services.leave_service import LeaveService

router = Router(name="leave")


def _parse_date(value: str):
    normalized = " ".join(value.split()).strip()
    return datetime.strptime(normalized, "%Y-%m-%d").date()


def _leave_type_label(language, leave_type: LeaveType) -> str:
    mapping = {
        LeaveType.VACATION: t(language, uz="Ta'til", ru="Отпуск", en="Vacation"),
        LeaveType.SICK: t(language, uz="Kasallik", ru="Больничный", en="Sick"),
        LeaveType.PERSONAL: t(language, uz="Shaxsiy", ru="Личное", en="Personal"),
    }
    return mapping.get(leave_type, leave_type.value)


def _format_leave_preview(language, leave_type: LeaveType, from_date, to_date, reason: str) -> str:
    return "\n".join(
        [
            t(language, uz="Ta'til so'rovi", ru="Запрос на отпуск", en="Leave request"),
            t(language, uz=f"📂 Turi: {_leave_type_label(language, leave_type)}", ru=f"📂 Тип: {_leave_type_label(language, leave_type)}", en=f"📂 Type: {_leave_type_label(language, leave_type)}"),
            t(language, uz=f"📅 Boshlanish: {from_date.isoformat()}", ru=f"📅 Начало: {from_date.isoformat()}", en=f"📅 From: {from_date.isoformat()}"),
            t(language, uz=f"📅 Tugash: {to_date.isoformat()}", ru=f"📅 Окончание: {to_date.isoformat()}", en=f"📅 To: {to_date.isoformat()}"),
            t(language, uz=f"📝 Sabab: {reason}", ru=f"📝 Причина: {reason}", en=f"📝 Reason: {reason}"),
        ]
    )


def _format_leave_created(language, leave_request) -> str:
    return "\n".join(
        [
            t(language, uz="Ta'til so'rovi yuborildi.", ru="Запрос на отпуск отправлен.", en="Leave request submitted."),
            t(language, uz=f"📂 Turi: {_leave_type_label(language, leave_request.leave_type)}", ru=f"📂 Тип: {_leave_type_label(language, leave_request.leave_type)}", en=f"📂 Type: {_leave_type_label(language, leave_request.leave_type)}"),
            t(language, uz=f"📅 Sana oralig'i: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}", ru=f"📅 Период: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}", en=f"📅 Period: {leave_request.from_date.isoformat()} - {leave_request.to_date.isoformat()}"),
            t(language, uz="📌 Status: Kutilmoqda", ru="📌 Статус: Ожидает", en="📌 Status: Pending"),
        ]
    )


async def _cancel_leave_flow(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await message.answer(
        t(
            access.user.language,
            uz="Ta'til so'rovi bekor qilindi.",
            ru="Запрос на отпуск отменен.",
            en="The leave request was cancelled.",
        )
    )
    await show_employee_panel(message, access, session)


@router.message(LocalizedTextFilter(*leave_request_button_texts()))
async def leave_request_entry_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    await state.clear()
    await state.set_state(LeaveRequestStates.waiting_for_type)
    await message.answer(
        t(
            access.user.language,
            uz="Ta'til turini tanlang.",
            ru="Выберите тип отпуска.",
            en="Choose the leave type.",
        ),
        reply_markup=build_leave_type_keyboard(access.user.language),
    )


@router.message(LeaveRequestStates.waiting_for_type, LocalizedTextFilter(*cancel_button_texts()))
@router.message(LeaveRequestStates.waiting_for_from_date, LocalizedTextFilter(*cancel_button_texts()))
@router.message(LeaveRequestStates.waiting_for_to_date, LocalizedTextFilter(*cancel_button_texts()))
@router.message(LeaveRequestStates.waiting_for_reason, LocalizedTextFilter(*cancel_button_texts()))
@router.message(LeaveRequestStates.waiting_for_confirmation, LocalizedTextFilter(*cancel_button_texts()))
async def leave_request_cancel_message_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await _cancel_leave_flow(message, state, session, settings)


@router.callback_query(F.data == "leave:cancel")
async def leave_request_cancel_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer(
        t(
            access.user.language,
            uz="Ta'til so'rovi bekor qilindi.",
            ru="Запрос на отпуск отменен.",
            en="The leave request was cancelled.",
        )
    )
    await callback.message.edit_text(
        t(
            access.user.language,
            uz="Ta'til so'rovi bekor qilindi.",
            ru="Запрос на отпуск отменен.",
            en="The leave request was cancelled.",
        )
    )
    await show_employee_panel(callback.message, access, session)


@router.callback_query(LeaveRequestStates.waiting_for_type, F.data.startswith("leave:type:"))
async def leave_request_type_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.data is None or callback.message is None:
        return

    raw_type = callback.data.rsplit(":", 1)[-1]
    try:
        leave_type = LeaveType(raw_type)
    except ValueError:
        await callback.answer(
            t(
                access.user.language,
                uz="Noto'g'ri ta'til turi tanlandi.",
                ru="Выбран некорректный тип отпуска.",
                en="An invalid leave type was selected.",
            ),
            show_alert=True,
        )
        return

    await state.update_data(leave_type=leave_type.value)
    await state.set_state(LeaveRequestStates.waiting_for_from_date)
    await callback.answer()
    await callback.message.edit_text(
        t(
            access.user.language,
            uz="Boshlanish sanasini yuboring. Format: YYYY-MM-DD",
            ru="Отправьте дату начала. Формат: YYYY-MM-DD",
            en="Send the start date. Format: YYYY-MM-DD",
        )
    )
    await callback.message.answer(
        t(
            access.user.language,
            uz="Jarayonni bekor qilish uchun tugmadan foydalaning.",
            ru="Используйте кнопку, чтобы отменить процесс.",
            en="Use the button to cancel the process.",
        ),
        reply_markup=build_employee_cancel_keyboard(access.user.language),
    )


@router.message(LeaveRequestStates.waiting_for_from_date)
async def leave_request_from_date_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    try:
        from_date = _parse_date(message.text or "")
    except ValueError:
        await message.answer(
            t(
                access.user.language,
                uz="Sana formati noto'g'ri. Format: YYYY-MM-DD",
                ru="Неверный формат даты. Формат: YYYY-MM-DD",
                en="Invalid date format. Use YYYY-MM-DD",
            )
        )
        return

    await state.update_data(from_date=from_date.isoformat())
    await state.set_state(LeaveRequestStates.waiting_for_to_date)
    await message.answer(
        t(
            access.user.language,
            uz="Tugash sanasini yuboring. Format: YYYY-MM-DD",
            ru="Отправьте дату окончания. Формат: YYYY-MM-DD",
            en="Send the end date. Format: YYYY-MM-DD",
        )
    )


@router.message(LeaveRequestStates.waiting_for_to_date)
async def leave_request_to_date_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    try:
        to_date = _parse_date(message.text or "")
    except ValueError:
        await message.answer(
            t(
                access.user.language,
                uz="Sana formati noto'g'ri. Format: YYYY-MM-DD",
                ru="Неверный формат даты. Формат: YYYY-MM-DD",
                en="Invalid date format. Use YYYY-MM-DD",
            )
        )
        return

    await state.update_data(to_date=to_date.isoformat())
    await state.set_state(LeaveRequestStates.waiting_for_reason)
    await message.answer(
        t(
            access.user.language,
            uz="Ta'til sababini yozing.",
            ru="Напишите причину отпуска.",
            en="Write the reason for the leave request.",
        )
    )


@router.message(LeaveRequestStates.waiting_for_reason)
async def leave_request_reason_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    reason = " ".join((message.text or "").split()).strip()
    if not reason:
        await message.answer(
            t(
                access.user.language,
                uz="Sabab bo'sh bo'lmasin.",
                ru="Причина не должна быть пустой.",
                en="The reason cannot be empty.",
            )
        )
        return

    await state.update_data(reason=reason)
    data = await state.get_data()
    leave_type = LeaveType(str(data["leave_type"]))
    from_date = _parse_date(str(data["from_date"]))
    to_date = _parse_date(str(data["to_date"]))
    await state.set_state(LeaveRequestStates.waiting_for_confirmation)
    await message.answer(
        _format_leave_preview(access.user.language, leave_type, from_date, to_date, reason),
        reply_markup=build_leave_confirmation_keyboard(access.user.language),
    )


@router.callback_query(LeaveRequestStates.waiting_for_confirmation, F.data == "leave:confirm")
async def leave_request_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.message is None:
        return

    data = await state.get_data()
    leave_type = LeaveType(str(data["leave_type"]))
    from_date = _parse_date(str(data["from_date"]))
    to_date = _parse_date(str(data["to_date"]))
    reason = str(data["reason"])

    leave_service = LeaveService(session)
    try:
        leave_request = await leave_service.create_leave_request(
            access,
            LeaveRequestCreateDTO(
                company_id=access.company.id,
                employee_id=access.employee.id,
                leave_type=leave_type,
                from_date=from_date,
                to_date=to_date,
                reason=reason,
            ),
        )
    except LeaveRequestValidationError:
        await callback.answer(
            t(
                access.user.language,
                uz="Ta'til so'rovi ma'lumotlari noto'g'ri.",
                ru="Данные запроса на отпуск некорректны.",
                en="The leave request data is invalid.",
            ),
            show_alert=True,
        )
        return

    await LeaveNotificationService(session).notify_company_admin(
        callback.bot,
        access=access,
        leave_request=leave_request,
    )
    await state.clear()
    await callback.answer(
        t(
            access.user.language,
            uz="Ta'til so'rovi yuborildi.",
            ru="Запрос на отпуск отправлен.",
            en="Leave request submitted.",
        )
    )
    await callback.message.edit_text(_format_leave_created(access.user.language, leave_request))
    await show_employee_panel(callback.message, access, session)
