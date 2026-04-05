from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin import show_shift_menu
from app.bot.handlers.company_admin_common import require_company_admin_callback, require_company_admin_message
from app.bot.keyboards.inline.common import build_confirmation_keyboard, build_yes_no_keyboard
from app.bot.keyboards.inline.shifts import build_shift_detail_keyboard, build_shift_list_keyboard
from app.bot.keyboards.reply.company_admin import (
    add_shift_button_texts,
    back_button_texts,
    build_company_admin_flow_back_keyboard,
    shift_list_button_texts,
)
from app.bot.states.shift_states import ShiftCreateStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.shift_dto import ShiftCreateDTO, ShiftDTO, ShiftUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    InvalidWorkDaysError,
    ShiftAlreadyExistsError,
    ShiftDeleteRestrictedError,
    ShiftNotFoundError,
)
from app.services.shift_service import ShiftService

router = Router(name="shifts")
SHIFT_PAGE_SIZE = ShiftService.DEFAULT_PAGE_SIZE


def _format_shift_detail(language, shift: ShiftDTO) -> str:
    status = t(language, uz="Faol" if shift.is_active else "Nofaol", ru="Активна" if shift.is_active else "Неактивна", en="Active" if shift.is_active else "Inactive")
    work_days = ", ".join(shift.work_days)
    return "\n".join(
        [
            t(language, uz=f"⏰ Smena: {shift.name}", ru=f"⏰ Смена: {shift.name}", en=f"⏰ Shift: {shift.name}"),
            t(language, uz=f"🕘 Boshlanish: {shift.start_time.strftime('%H:%M')}", ru=f"🕘 Начало: {shift.start_time.strftime('%H:%M')}", en=f"🕘 Start: {shift.start_time.strftime('%H:%M')}"),
            t(language, uz=f"🕔 Tugash: {shift.end_time.strftime('%H:%M')}", ru=f"🕔 Конец: {shift.end_time.strftime('%H:%M')}", en=f"🕔 End: {shift.end_time.strftime('%H:%M')}"),
            t(language, uz=f"⏱ Kechikish: {shift.late_after_minutes} daqiqa", ru=f"⏱ Опоздание: {shift.late_after_minutes} минут", en=f"⏱ Late after: {shift.late_after_minutes} minutes"),
            t(language, uz=f"⏳ Erta ketish: {shift.early_leave_before_minutes} daqiqa", ru=f"⏳ Ранний уход: {shift.early_leave_before_minutes} минут", en=f"⏳ Early leave: {shift.early_leave_before_minutes} minutes"),
            t(language, uz=f"📅 Ish kunlari: {work_days}", ru=f"📅 Рабочие дни: {work_days}", en=f"📅 Work days: {work_days}"),
            t(language, uz=f"🔁 Holati: {status}", ru=f"🔁 Статус: {status}", en=f"🔁 Status: {status}"),
        ]
    )


@router.message(StateFilter(None), LocalizedTextFilter(*add_shift_button_texts()))
async def add_shift_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await state.set_state(ShiftCreateStates.waiting_for_name)
    await message.answer(
        t(access.user.language, uz="Smena nomini yuboring.", ru="Отправьте название смены.", en="Send the shift name."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.callback_query(F.data.startswith("shift:edit:"))
async def shift_edit_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    try:
        shift = await ShiftService(session).get_shift(access.company.id, int(shift_id_raw))
    except ShiftNotFoundError:
        await callback.answer(t(access.user.language, uz="Smena topilmadi.", ru="Смена не найдена.", en="Shift not found."), show_alert=True)
        return
    await state.clear()
    await state.update_data(shift_id=int(shift_id_raw), page=int(page_raw), is_edit=True, is_active=shift.is_active)
    await state.set_state(ShiftCreateStates.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        t(access.user.language, uz=f"Yangi smena nomini yuboring.\nJoriy nom: {shift.name}", ru=f"Отправьте новое название смены.\nТекущее название: {shift.name}", en=f"Send the new shift name.\nCurrent name: {shift.name}"),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(StateFilter(None), LocalizedTextFilter(*shift_list_button_texts()))
async def shift_list_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    page = await ShiftService(session).list_shifts(access.company.id, page=1, page_size=SHIFT_PAGE_SIZE)
    await message.answer(
        t(access.user.language, uz=f"Smenalar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список смен ({page.page}/{page.total_pages})", en=f"Shift list ({page.page}/{page.total_pages})"),
        reply_markup=build_shift_list_keyboard(page, access.user.language),
    )


@router.message(ShiftCreateStates.waiting_for_name, LocalizedTextFilter(*back_button_texts()))
@router.message(ShiftCreateStates.waiting_for_start_time, LocalizedTextFilter(*back_button_texts()))
@router.message(ShiftCreateStates.waiting_for_end_time, LocalizedTextFilter(*back_button_texts()))
@router.message(ShiftCreateStates.waiting_for_late_after, LocalizedTextFilter(*back_button_texts()))
@router.message(ShiftCreateStates.waiting_for_early_before, LocalizedTextFilter(*back_button_texts()))
@router.message(ShiftCreateStates.waiting_for_work_days, LocalizedTextFilter(*back_button_texts()))
async def shift_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_shift_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(ShiftCreateStates.waiting_for_name)
async def shift_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    normalized_name = ShiftService.normalize_name(message.text or "")
    if not normalized_name:
        await message.answer(t(access.user.language, uz="Smena nomi bo'sh bo'lmasin.", ru="Название смены не должно быть пустым.", en="Shift name cannot be empty."))
        return
    await state.update_data(name=normalized_name)
    await state.set_state(ShiftCreateStates.waiting_for_start_time)
    await message.answer(t(access.user.language, uz="Boshlanish vaqtini yuboring. Format: HH:MM", ru="Отправьте время начала. Формат: HH:MM", en="Send the start time. Format: HH:MM"))


@router.message(ShiftCreateStates.waiting_for_start_time)
async def shift_start_time_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        start_time = ShiftService.parse_time_value(message.text or "")
    except ValueError:
        await message.answer(t(access.user.language, uz="Vaqt noto'g'ri. Format HH:MM bo'lsin.", ru="Некорректное время. Используйте формат HH:MM.", en="Invalid time. Use HH:MM format."))
        return
    await state.update_data(start_time=start_time.isoformat(timespec="minutes"))
    await state.set_state(ShiftCreateStates.waiting_for_end_time)
    await message.answer(t(access.user.language, uz="Tugash vaqtini yuboring. Format: HH:MM", ru="Отправьте время окончания. Формат: HH:MM", en="Send the end time. Format: HH:MM"))


@router.message(ShiftCreateStates.waiting_for_end_time)
async def shift_end_time_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        end_time = ShiftService.parse_time_value(message.text or "")
    except ValueError:
        await message.answer(t(access.user.language, uz="Vaqt noto'g'ri. Format HH:MM bo'lsin.", ru="Некорректное время. Используйте формат HH:MM.", en="Invalid time. Use HH:MM format."))
        return
    await state.update_data(end_time=end_time.isoformat(timespec="minutes"))
    await state.set_state(ShiftCreateStates.waiting_for_late_after)
    await message.answer(t(access.user.language, uz="Kechikish necha daqiqadan keyin hisoblansin?", ru="Через сколько минут считать опоздание?", en="After how many minutes should lateness start?"))


@router.message(ShiftCreateStates.waiting_for_late_after)
async def shift_late_after_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        late_after = ShiftService.parse_minutes_value(message.text or "")
    except InvalidWorkDaysError:
        await message.answer(t(access.user.language, uz="Faqat musbat yoki nol butun son yuboring.", ru="Отправьте целое число больше или равно нулю.", en="Send a whole number greater than or equal to zero."))
        return
    await state.update_data(late_after_minutes=late_after)
    await state.set_state(ShiftCreateStates.waiting_for_early_before)
    await message.answer(t(access.user.language, uz="Erta ketish necha daqiqadan oldin hisoblansin?", ru="За сколько минут считать ранний уход?", en="How many minutes before end time should early leave be counted?"))


@router.message(ShiftCreateStates.waiting_for_early_before)
async def shift_early_before_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        early_before = ShiftService.parse_minutes_value(message.text or "")
    except InvalidWorkDaysError:
        await message.answer(t(access.user.language, uz="Faqat musbat yoki nol butun son yuboring.", ru="Отправьте целое число больше или равно нулю.", en="Send a whole number greater than or equal to zero."))
        return
    await state.update_data(early_leave_before_minutes=early_before)
    await state.set_state(ShiftCreateStates.waiting_for_work_days)
    await message.answer(t(access.user.language, uz="Ish kunlarini yuboring. Masalan: MON,TUE,WED,THU,FRI", ru="Отправьте рабочие дни. Например: MON,TUE,WED,THU,FRI", en="Send work days. Example: MON,TUE,WED,THU,FRI"))


@router.message(ShiftCreateStates.waiting_for_work_days)
async def shift_work_days_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    service = ShiftService(session)
    try:
        work_days = service.parse_work_days(message.text or "")
    except InvalidWorkDaysError:
        await message.answer(t(access.user.language, uz="Ish kunlari noto'g'ri. MON,TUE,... formatida yuboring.", ru="Некорректные рабочие дни. Используйте формат MON,TUE,...", en="Invalid work days. Use MON,TUE,... format."))
        return
    data = await state.get_data()
    await state.set_state(ShiftCreateStates.waiting_for_confirmation)
    await state.update_data(work_days=work_days)
    await message.answer(
        "\n".join(
            [
                t(access.user.language, uz="Yangi smenani tasdiqlang.", ru="Подтвердите новую смену.", en="Confirm the new shift."),
                t(access.user.language, uz=f"⏰ Nomi: {data.get('name', '-')}", ru=f"⏰ Название: {data.get('name', '-')}", en=f"⏰ Name: {data.get('name', '-')}"),
                t(access.user.language, uz=f"🕘 Boshlanish: {data.get('start_time', '-')}", ru=f"🕘 Начало: {data.get('start_time', '-')}", en=f"🕘 Start: {data.get('start_time', '-')}"),
                t(access.user.language, uz=f"🕔 Tugash: {data.get('end_time', '-')}", ru=f"🕔 Конец: {data.get('end_time', '-')}", en=f"🕔 End: {data.get('end_time', '-')}"),
                t(access.user.language, uz=f"⏱ Kechikish: {data.get('late_after_minutes', 0)}", ru=f"⏱ Опоздание: {data.get('late_after_minutes', 0)}", en=f"⏱ Late after: {data.get('late_after_minutes', 0)}"),
                t(access.user.language, uz=f"⏳ Erta ketish: {data.get('early_leave_before_minutes', 0)}", ru=f"⏳ Ранний уход: {data.get('early_leave_before_minutes', 0)}", en=f"⏳ Early leave: {data.get('early_leave_before_minutes', 0)}"),
                t(access.user.language, uz=f"📅 Ish kunlari: {', '.join(work_days)}", ru=f"📅 Рабочие дни: {', '.join(work_days)}", en=f"📅 Work days: {', '.join(work_days)}"),
            ]
        ),
        reply_markup=build_confirmation_keyboard("shift:create:confirm", "shift:create:cancel", access.user.language),
    )


@router.message(ShiftCreateStates.waiting_for_confirmation)
async def shift_waiting_confirmation_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, inline tasdiqlash tugmalaridan foydalaning.", ru="Пожалуйста, используйте inline-кнопки подтверждения.", en="Please use the inline confirmation buttons."))


@router.callback_query(ShiftCreateStates.waiting_for_confirmation, F.data == "shift:create:confirm")
async def shift_create_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    service = ShiftService(session)
    try:
        if data.get("is_edit"):
            shift = await service.update_shift(
                access.company.id,
                int(data.get("shift_id", 0)),
                ShiftUpdateDTO(
                    name=str(data.get("name", "")),
                    start_time=service.parse_time_value(str(data.get("start_time", "00:00"))),
                    end_time=service.parse_time_value(str(data.get("end_time", "00:00"))),
                    late_after_minutes=int(data.get("late_after_minutes", 0)),
                    early_leave_before_minutes=int(data.get("early_leave_before_minutes", 0)),
                    work_days=list(data.get("work_days", [])),
                    is_active=bool(data.get("is_active", True)),
                ),
                actor_telegram_id=access.user.telegram_id,
            )
        else:
            shift = await service.create_shift(
                access.company.id,
                ShiftCreateDTO(
                    name=str(data.get("name", "")),
                    start_time=service.parse_time_value(str(data.get("start_time", "00:00"))),
                    end_time=service.parse_time_value(str(data.get("end_time", "00:00"))),
                    late_after_minutes=int(data.get("late_after_minutes", 0)),
                    early_leave_before_minutes=int(data.get("early_leave_before_minutes", 0)),
                    work_days=list(data.get("work_days", [])),
                ),
                actor_telegram_id=access.user.telegram_id,
            )
    except ShiftAlreadyExistsError:
        await callback.answer(t(access.user.language, uz="Bunday smena allaqachon mavjud.", ru="Такая смена уже существует.", en="This shift already exists."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Smena saqlandi.", ru="Смена сохранена.", en="Shift saved."))
    await callback.message.edit_text(
        _format_shift_detail(access.user.language, shift),
        reply_markup=build_shift_detail_keyboard(shift, 1, access.user.language),
    )


@router.callback_query(ShiftCreateStates.waiting_for_confirmation, F.data == "shift:create:cancel")
async def shift_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(t(access.user.language, uz="Smena yaratish bekor qilindi.", ru="Создание смены отменено.", en="Shift creation cancelled."))
    await show_shift_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "shift:noop")
async def shift_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("shift:list:"))
async def shift_list_callback_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    page_number = int(callback.data.rsplit(":", 1)[-1])
    page = await ShiftService(session).list_shifts(access.company.id, page=page_number, page_size=SHIFT_PAGE_SIZE)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz=f"Smenalar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список смен ({page.page}/{page.total_pages})", en=f"Shift list ({page.page}/{page.total_pages})"),
        reply_markup=build_shift_list_keyboard(page, access.user.language),
    )


@router.callback_query(F.data.startswith("shift:detail:"))
async def shift_detail_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    try:
        shift = await ShiftService(session).get_shift(access.company.id, int(shift_id_raw))
    except ShiftNotFoundError:
        await callback.answer(t(access.user.language, uz="Smena topilmadi.", ru="Смена не найдена.", en="Shift not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_shift_detail(access.user.language, shift),
        reply_markup=build_shift_detail_keyboard(shift, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("shift:toggle:"))
async def shift_toggle_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    try:
        shift = await ShiftService(session).toggle_shift_status(access.company.id, int(shift_id_raw), actor_telegram_id=access.user.telegram_id)
    except ShiftNotFoundError:
        await callback.answer(t(access.user.language, uz="Smena topilmadi.", ru="Смена не найдена.", en="Shift not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_shift_detail(access.user.language, shift),
        reply_markup=build_shift_detail_keyboard(shift, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("shift:delete:"))
async def shift_delete_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Rostdan ham smenani o'chirmoqchimisiz?", ru="Вы действительно хотите удалить смену?", en="Do you really want to delete this shift?"),
        reply_markup=build_yes_no_keyboard(
            f"shift:delete_confirm:{shift_id_raw}:{page_raw}",
            f"shift:delete_cancel:{shift_id_raw}:{page_raw}",
            access.user.language,
        ),
    )


@router.callback_query(F.data.startswith("shift:delete_confirm:"))
async def shift_delete_confirm_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    service = ShiftService(session)
    try:
        await service.delete_shift(access.company.id, int(shift_id_raw), actor_telegram_id=access.user.telegram_id)
    except ShiftDeleteRestrictedError:
        await callback.answer(t(access.user.language, uz="Smenaga ishchilar bog'langan. Avval ularni ko'chiring yoki smenani deaktiv qiling.", ru="К смене привязаны сотрудники. Сначала перенесите их или деактивируйте смену.", en="This shift has linked employees. Move them first or deactivate the shift."), show_alert=True)
        return
    except ShiftNotFoundError:
        await callback.answer(t(access.user.language, uz="Smena topilmadi.", ru="Смена не найдена.", en="Shift not found."), show_alert=True)
        return
    page = await service.list_shifts(access.company.id, page=int(page_raw), page_size=SHIFT_PAGE_SIZE)
    await callback.answer(t(access.user.language, uz="Smena o'chirildi.", ru="Смена удалена.", en="Shift deleted."))
    await callback.message.edit_text(
        t(access.user.language, uz=f"Smenalar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список смен ({page.page}/{page.total_pages})", en=f"Shift list ({page.page}/{page.total_pages})"),
        reply_markup=build_shift_list_keyboard(page, access.user.language),
    )


@router.callback_query(F.data.startswith("shift:delete_cancel:"))
async def shift_delete_cancel_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, shift_id_raw, page_raw = callback.data.split(":", 3)
    try:
        shift = await ShiftService(session).get_shift(access.company.id, int(shift_id_raw))
    except ShiftNotFoundError:
        await callback.answer(t(access.user.language, uz="Smena topilmadi.", ru="Смена не найдена.", en="Shift not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_shift_detail(access.user.language, shift),
        reply_markup=build_shift_detail_keyboard(shift, int(page_raw), access.user.language),
    )
