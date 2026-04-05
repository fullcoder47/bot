from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.employee_common import (
    format_attendance_record_detail,
    require_employee_callback,
    require_employee_message,
)
from app.bot.keyboards.inline.attendance import build_history_detail_keyboard, build_history_keyboard
from app.bot.keyboards.reply.employee import history_button_texts
from app.core.config import Settings
from app.core.localization import t
from app.domain.exceptions.attendance_exceptions import AttendanceSessionNotFoundError
from app.services.attendance_service import AttendanceService

router = Router(name="history")


def _format_history_list_header(language, page: int, total_pages: int) -> str:
    return t(
        language,
        uz=f"Attendance tarixingiz ({page}/{total_pages})",
        ru=f"Ваша история attendance ({page}/{total_pages})",
        en=f"Your attendance history ({page}/{total_pages})",
    )


@router.message(StateFilter(None), LocalizedTextFilter(*history_button_texts()))
async def employee_history_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return

    history_page = await AttendanceService(session).get_history(access, page=1)
    if not history_page.items:
        await message.answer(
            t(
                access.user.language,
                uz="Attendance tarixingiz hali bo'sh.",
                ru="Ваша история attendance пока пуста.",
                en="Your attendance history is empty for now.",
            )
        )
        return

    await message.answer(
        _format_history_list_header(access.user.language, history_page.page, history_page.total_pages),
        reply_markup=build_history_keyboard(history_page, access.user.language),
    )


@router.callback_query(F.data.startswith("attendance:history:page:"))
async def attendance_history_page_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.data is None or callback.message is None:
        return

    page = int(callback.data.rsplit(":", 1)[-1])
    history_page = await AttendanceService(session).get_history(access, page=page)
    if not history_page.items:
        await callback.answer(
            t(
                access.user.language,
                uz="Bu sahifada yozuvlar topilmadi.",
                ru="На этой странице записи не найдены.",
                en="No records were found on this page.",
            ),
            show_alert=True,
        )
        return

    await callback.answer()
    await callback.message.edit_text(
        _format_history_list_header(access.user.language, history_page.page, history_page.total_pages),
        reply_markup=build_history_keyboard(history_page, access.user.language),
    )


@router.callback_query(F.data.startswith("attendance:history:detail:"))
async def attendance_history_detail_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_callback(callback, session, settings)
    if access is None or callback.data is None or callback.message is None:
        return

    _, _, _, record_id_raw, page_raw = callback.data.split(":", 4)
    page = int(page_raw)

    try:
        record = await AttendanceService(session).get_history_record(access, int(record_id_raw))
    except AttendanceSessionNotFoundError:
        await callback.answer(
            t(
                access.user.language,
                uz="Attendance yozuvi topilmadi.",
                ru="Attendance-запись не найдена.",
                en="Attendance record not found.",
            ),
            show_alert=True,
        )
        return

    await callback.answer()
    await callback.message.edit_text(
        format_attendance_record_detail(access.user.language, record),
        reply_markup=build_history_detail_keyboard(page, access.user.language),
    )
