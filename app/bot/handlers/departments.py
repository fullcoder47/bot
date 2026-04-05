from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin import show_department_menu
from app.bot.handlers.company_admin_common import require_company_admin_callback, require_company_admin_message
from app.bot.keyboards.inline.common import build_confirmation_keyboard, build_yes_no_keyboard
from app.bot.keyboards.inline.departments import build_department_detail_keyboard, build_department_list_keyboard
from app.bot.keyboards.reply.company_admin import (
    add_department_button_texts,
    back_button_texts,
    build_company_admin_flow_back_keyboard,
    department_list_button_texts,
)
from app.bot.states.department_states import DepartmentCreateStates, DepartmentEditStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.department_dto import DepartmentCreateDTO, DepartmentDTO, DepartmentUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    DepartmentAlreadyExistsError,
    DepartmentDeleteRestrictedError,
    DepartmentNotFoundError,
)
from app.services.department_service import DepartmentService

router = Router(name="departments")
DEPARTMENT_PAGE_SIZE = DepartmentService.DEFAULT_PAGE_SIZE


def _format_department_detail(language, department: DepartmentDTO) -> str:
    status = t(language, uz="Faol" if department.is_active else "Nofaol", ru="Активен" if department.is_active else "Неактивен", en="Active" if department.is_active else "Inactive")
    return "\n".join(
        [
            t(language, uz=f"🗂 Bo'lim: {department.name}", ru=f"🗂 Отдел: {department.name}", en=f"🗂 Department: {department.name}"),
            t(language, uz=f"🔁 Holati: {status}", ru=f"🔁 Статус: {status}", en=f"🔁 Status: {status}"),
        ]
    )


@router.message(LocalizedTextFilter(*add_department_button_texts()))
async def add_department_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await state.set_state(DepartmentCreateStates.waiting_for_name)
    await message.answer(
        t(access.user.language, uz="Bo'lim nomini yuboring.", ru="Отправьте название отдела.", en="Send the department name."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(LocalizedTextFilter(*department_list_button_texts()))
async def department_list_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    page = await DepartmentService(session).list_departments(access.company.id, page=1, page_size=DEPARTMENT_PAGE_SIZE)
    await message.answer(
        t(access.user.language, uz=f"Bo'limlar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список отделов ({page.page}/{page.total_pages})", en=f"Department list ({page.page}/{page.total_pages})"),
        reply_markup=build_department_list_keyboard(page, access.user.language),
    )


@router.message(DepartmentCreateStates.waiting_for_name, LocalizedTextFilter(*back_button_texts()))
@router.message(DepartmentCreateStates.waiting_for_confirmation, LocalizedTextFilter(*back_button_texts()))
@router.message(DepartmentEditStates.waiting_for_name, LocalizedTextFilter(*back_button_texts()))
@router.message(DepartmentEditStates.waiting_for_confirmation, LocalizedTextFilter(*back_button_texts()))
async def department_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_department_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(DepartmentCreateStates.waiting_for_name)
async def department_create_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    normalized_name = DepartmentService.normalize_name(message.text or "")
    if not normalized_name:
        await message.answer(t(access.user.language, uz="Bo'lim nomi bo'sh bo'lmasin.", ru="Название отдела не должно быть пустым.", en="Department name cannot be empty."))
        return
    await state.update_data(name=normalized_name)
    await state.set_state(DepartmentCreateStates.waiting_for_confirmation)
    await message.answer(
        t(access.user.language, uz=f"Yangi bo'limni tasdiqlang:\n{message.text or '-'}", ru=f"Подтвердите новый отдел:\n{message.text or '-'}", en=f"Confirm the new department:\n{message.text or '-'}"),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )
    await message.answer(
        t(access.user.language, uz="Tasdiqlaysizmi?", ru="Подтверждаете?", en="Confirm?"),
        reply_markup=build_confirmation_keyboard("department:create:confirm", "department:create:cancel", access.user.language),
    )


@router.message(DepartmentCreateStates.waiting_for_confirmation)
@router.message(DepartmentEditStates.waiting_for_confirmation)
async def department_waiting_confirmation_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, inline tasdiqlash tugmalaridan foydalaning.", ru="Пожалуйста, используйте inline-кнопки подтверждения.", en="Please use the inline confirmation buttons."))


@router.callback_query(DepartmentCreateStates.waiting_for_confirmation, F.data == "department:create:confirm")
async def department_create_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    try:
        department = await DepartmentService(session).create_department(
            access.company.id,
            DepartmentCreateDTO(name=str(data.get("name", ""))),
            actor_telegram_id=access.user.telegram_id,
        )
    except DepartmentAlreadyExistsError:
        await callback.answer(t(access.user.language, uz="Bunday bo'lim allaqachon mavjud.", ru="Такой отдел уже существует.", en="This department already exists."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Bo'lim yaratildi.", ru="Отдел создан.", en="Department created."))
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, 1, access.user.language),
    )


@router.callback_query(DepartmentCreateStates.waiting_for_confirmation, F.data == "department:create:cancel")
async def department_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(t(access.user.language, uz="Bo'lim yaratish bekor qilindi.", ru="Создание отдела отменено.", en="Department creation cancelled."))
    await show_department_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "department:noop")
async def department_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("department:list:"))
async def department_list_callback_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    page_number = int(callback.data.rsplit(":", 1)[-1])
    page = await DepartmentService(session).list_departments(access.company.id, page=page_number, page_size=DEPARTMENT_PAGE_SIZE)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz=f"Bo'limlar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список отделов ({page.page}/{page.total_pages})", en=f"Department list ({page.page}/{page.total_pages})"),
        reply_markup=build_department_list_keyboard(page, access.user.language),
    )


@router.callback_query(F.data.startswith("department:detail:"))
async def department_detail_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    try:
        department = await DepartmentService(session).get_department(access.company.id, int(department_id_raw))
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("department:edit:"))
async def department_edit_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    try:
        department = await DepartmentService(session).get_department(access.company.id, int(department_id_raw))
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    await state.clear()
    await state.update_data(department_id=int(department_id_raw), page=int(page_raw))
    await state.set_state(DepartmentEditStates.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        t(access.user.language, uz=f"Yangi bo'lim nomini yuboring.\nJoriy nom: {department.name}", ru=f"Отправьте новое название отдела.\nТекущее название: {department.name}", en=f"Send the new department name.\nCurrent name: {department.name}"),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(DepartmentEditStates.waiting_for_name)
async def department_edit_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    normalized_name = DepartmentService.normalize_name(message.text or "")
    if not normalized_name:
        await message.answer(t(access.user.language, uz="Bo'lim nomi bo'sh bo'lmasin.", ru="Название отдела не должно быть пустым.", en="Department name cannot be empty."))
        return
    await state.update_data(name=normalized_name)
    await state.set_state(DepartmentEditStates.waiting_for_confirmation)
    await message.answer(
        t(access.user.language, uz=f"Yangi nomni tasdiqlang:\n{message.text or '-'}", ru=f"Подтвердите новое имя:\n{message.text or '-'}", en=f"Confirm the new name:\n{message.text or '-'}"),
        reply_markup=build_confirmation_keyboard("department:edit:confirm", "department:edit:cancel", access.user.language),
    )


@router.callback_query(DepartmentEditStates.waiting_for_confirmation, F.data == "department:edit:confirm")
async def department_edit_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    department_id = int(data.get("department_id", 0))
    page = int(data.get("page", 1))
    current = await DepartmentService(session).get_department(access.company.id, department_id)
    try:
        department = await DepartmentService(session).update_department(
            access.company.id,
            department_id,
            DepartmentUpdateDTO(name=str(data.get("name", "")), is_active=current.is_active),
            actor_telegram_id=access.user.telegram_id,
        )
    except (DepartmentAlreadyExistsError, DepartmentNotFoundError):
        await callback.answer(t(access.user.language, uz="Bo'limni yangilab bo'lmadi.", ru="Не удалось обновить отдел.", en="Could not update the department."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Bo'lim yangilandi.", ru="Отдел обновлён.", en="Department updated."))
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, page, access.user.language),
    )


@router.callback_query(DepartmentEditStates.waiting_for_confirmation, F.data == "department:edit:cancel")
async def department_edit_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    department_id = int(data.get("department_id", 0))
    page = int(data.get("page", 1))
    await state.clear()
    try:
        department = await DepartmentService(session).get_department(access.company.id, department_id)
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, page, access.user.language),
    )


@router.callback_query(F.data.startswith("department:toggle:"))
async def department_toggle_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    try:
        department = await DepartmentService(session).toggle_department_status(access.company.id, int(department_id_raw), actor_telegram_id=access.user.telegram_id)
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("department:delete:"))
async def department_delete_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Rostdan ham bo'limni o'chirmoqchimisiz?", ru="Вы действительно хотите удалить отдел?", en="Do you really want to delete this department?"),
        reply_markup=build_yes_no_keyboard(
            f"department:delete_confirm:{department_id_raw}:{page_raw}",
            f"department:delete_cancel:{department_id_raw}:{page_raw}",
            access.user.language,
        ),
    )


@router.callback_query(F.data.startswith("department:delete_confirm:"))
async def department_delete_confirm_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    service = DepartmentService(session)
    try:
        await service.delete_department(access.company.id, int(department_id_raw), actor_telegram_id=access.user.telegram_id)
    except DepartmentDeleteRestrictedError:
        await callback.answer(t(access.user.language, uz="Bo'limga ishchilar bog'langan. Avval ularni ko'chiring yoki bo'limni deaktiv qiling.", ru="К отделу привязаны сотрудники. Сначала перенесите их или деактивируйте отдел.", en="This department has linked employees. Move them first or deactivate the department."), show_alert=True)
        return
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    page = await service.list_departments(access.company.id, page=int(page_raw), page_size=DEPARTMENT_PAGE_SIZE)
    await callback.answer(t(access.user.language, uz="Bo'lim o'chirildi.", ru="Отдел удалён.", en="Department deleted."))
    await callback.message.edit_text(
        t(access.user.language, uz=f"Bo'limlar ro'yxati ({page.page}/{page.total_pages})", ru=f"Список отделов ({page.page}/{page.total_pages})", en=f"Department list ({page.page}/{page.total_pages})"),
        reply_markup=build_department_list_keyboard(page, access.user.language),
    )


@router.callback_query(F.data.startswith("department:delete_cancel:"))
async def department_delete_cancel_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, department_id_raw, page_raw = callback.data.split(":", 3)
    try:
        department = await DepartmentService(session).get_department(access.company.id, int(department_id_raw))
    except DepartmentNotFoundError:
        await callback.answer(t(access.user.language, uz="Bo'lim topilmadi.", ru="Отдел не найден.", en="Department not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_department_detail(access.user.language, department),
        reply_markup=build_department_detail_keyboard(department, int(page_raw), access.user.language),
    )
