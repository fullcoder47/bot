from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin import show_employee_menu
from app.bot.handlers.company_admin_common import require_company_admin_callback, require_company_admin_message
from app.bot.keyboards.inline.common import build_confirmation_keyboard
from app.bot.keyboards.inline.employees import (
    build_employee_assignment_keyboard,
    build_employee_detail_keyboard,
    build_employee_edit_menu_keyboard,
    build_employee_filter_keyboard,
    build_employee_list_keyboard,
    build_option_selection_keyboard,
)
from app.bot.keyboards.reply.company_admin import (
    add_employee_button_texts,
    back_button_texts,
    build_company_admin_flow_back_keyboard,
    employee_filters_button_texts,
    employee_list_button_texts,
    employee_search_button_texts,
)
from app.bot.states.employee_states import EmployeeCreateStates, EmployeeEditStates, EmployeeSearchStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.employee_dto import EmployeeCreateDTO, EmployeeDetailDTO, EmployeeFiltersDTO, EmployeeUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    BranchAssignmentRequiredError,
    BranchNotFoundError,
    EmployeeAlreadyExistsError,
    EmployeeNotFoundError,
    ForeignEntityScopeError,
    InvalidPhoneError,
)
from app.services.branch_service import BranchService
from app.services.department_service import DepartmentService
from app.services.employee_service import EmployeeService
from app.services.shift_service import ShiftService

router = Router(name="employees")
EMPLOYEE_PAGE_SIZE = EmployeeService.DEFAULT_PAGE_SIZE
LIST_CONTEXT_KEY = "employee_list_context"
FILTER_DRAFT_KEY = "employee_filter_draft"


def _format_employee_detail(language, employee: EmployeeDetailDTO) -> str:
    status = t(language, uz="Faol" if employee.is_active else "Nofaol", ru="Активен" if employee.is_active else "Неактивен", en="Active" if employee.is_active else "Inactive")
    return "\n".join(
        [
            t(language, uz=f"👤 F.I.Sh: {employee.full_name}", ru=f"👤 Ф.И.О.: {employee.full_name}", en=f"👤 Full name: {employee.full_name}"),
            t(language, uz=f"📞 Telefon: {employee.phone or '-'}", ru=f"📞 Телефон: {employee.phone or '-'}", en=f"📞 Phone: {employee.phone or '-'}"),
            t(language, uz=f"🆔 Telegram ID: {employee.telegram_id or '-'}", ru=f"🆔 Telegram ID: {employee.telegram_id or '-'}", en=f"🆔 Telegram ID: {employee.telegram_id or '-'}"),
            t(language, uz=f"🏷 Kod: {employee.employee_code or '-'}", ru=f"🏷 Код: {employee.employee_code or '-'}", en=f"🏷 Code: {employee.employee_code or '-'}"),
            t(language, uz=f"💼 Lavozim: {employee.position or '-'}", ru=f"💼 Должность: {employee.position or '-'}", en=f"💼 Position: {employee.position or '-'}"),
            t(language, uz=f"🏢 Filial: {employee.branch.name if employee.branch else '-'}", ru=f"🏢 Филиал: {employee.branch.name if employee.branch else '-'}", en=f"🏢 Branch: {employee.branch.name if employee.branch else '-'}"),
            t(language, uz=f"🗂 Bo'lim: {employee.department.name if employee.department else '-'}", ru=f"🗂 Отдел: {employee.department.name if employee.department else '-'}", en=f"🗂 Department: {employee.department.name if employee.department else '-'}"),
            t(language, uz=f"⏰ Smena: {employee.shift.name if employee.shift else '-'}", ru=f"⏰ Смена: {employee.shift.name if employee.shift else '-'}", en=f"⏰ Shift: {employee.shift.name if employee.shift else '-'}"),
            t(language, uz=f"📅 Ishga kirgan sana: {employee.hire_date.isoformat() if employee.hire_date else '-'}", ru=f"📅 Дата найма: {employee.hire_date.isoformat() if employee.hire_date else '-'}", en=f"📅 Hire date: {employee.hire_date.isoformat() if employee.hire_date else '-'}"),
            t(language, uz=f"🔁 Holati: {status}", ru=f"🔁 Статус: {status}", en=f"🔁 Status: {status}"),
        ]
    )


def _serialize_filters(filters: EmployeeFiltersDTO) -> dict[str, object]:
    return {
        "search": filters.search,
        "is_active": filters.is_active,
        "branch_id": filters.branch_id,
        "department_id": filters.department_id,
        "shift_id": filters.shift_id,
    }


def _deserialize_filters(raw: dict[str, object] | None) -> EmployeeFiltersDTO:
    raw = raw or {}
    status = raw.get("is_active")
    return EmployeeFiltersDTO(
        search=raw.get("search") if isinstance(raw.get("search"), str) else None,
        is_active=status if isinstance(status, bool) else None,
        branch_id=raw.get("branch_id") if isinstance(raw.get("branch_id"), int) else None,
        department_id=raw.get("department_id") if isinstance(raw.get("department_id"), int) else None,
        shift_id=raw.get("shift_id") if isinstance(raw.get("shift_id"), int) else None,
    )


def _build_update_payload(employee: EmployeeDetailDTO, **changes) -> EmployeeUpdateDTO:
    return EmployeeUpdateDTO(
        full_name=changes.get("full_name", employee.full_name),
        phone=changes.get("phone", employee.phone),
        telegram_id=changes.get("telegram_id", employee.telegram_id),
        employee_code=changes.get("employee_code", employee.employee_code),
        position=changes.get("position", employee.position),
        branch_id=changes.get("branch_id", employee.branch.id if employee.branch else None),
        department_id=changes.get("department_id", employee.department.id if employee.department else None),
        shift_id=changes.get("shift_id", employee.shift.id if employee.shift else None),
        hire_date=changes.get("hire_date", employee.hire_date),
        is_active=changes.get("is_active", employee.is_active),
    )


async def _get_list_filters(state: FSMContext) -> EmployeeFiltersDTO:
    data = await state.get_data()
    return _deserialize_filters(data.get(LIST_CONTEXT_KEY) if isinstance(data.get(LIST_CONTEXT_KEY), dict) else None)


async def _set_list_filters(state: FSMContext, filters: EmployeeFiltersDTO) -> None:
    await state.update_data(**{LIST_CONTEXT_KEY: _serialize_filters(filters)})


async def _get_filter_draft(state: FSMContext) -> EmployeeFiltersDTO:
    data = await state.get_data()
    return _deserialize_filters(data.get(FILTER_DRAFT_KEY) if isinstance(data.get(FILTER_DRAFT_KEY), dict) else None)


async def _set_filter_draft(state: FSMContext, filters: EmployeeFiltersDTO) -> None:
    await state.update_data(**{FILTER_DRAFT_KEY: _serialize_filters(filters)})


async def _show_employee_list(
    message: Message,
    service: EmployeeService,
    company_id: int,
    language,
    state: FSMContext,
    page: int = 1,
) -> None:
    filters = await _get_list_filters(state)
    employee_page = await service.list_employees(company_id, page=page, page_size=EMPLOYEE_PAGE_SIZE, filters=filters)
    await message.answer(
        t(language, uz=f"Ishchilar ro'yxati ({employee_page.page}/{employee_page.total_pages})", ru=f"Список сотрудников ({employee_page.page}/{employee_page.total_pages})", en=f"Employee list ({employee_page.page}/{employee_page.total_pages})"),
        reply_markup=build_employee_list_keyboard(employee_page, language),
    )


@router.message(LocalizedTextFilter(*add_employee_button_texts()))
async def add_employee_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    branches = await BranchService(session).list_branch_options(access.company.id, active_only=True)
    if not branches:
        await message.answer(
            t(access.user.language, uz="Avval kamida bitta filial yarating.", ru="Сначала создайте хотя бы один филиал.", en="Create at least one branch first."),
        )
        return
    await state.clear()
    await state.set_state(EmployeeCreateStates.waiting_for_full_name)
    await message.answer(
        t(access.user.language, uz="Ishchining F.I.Sh ni yuboring.", ru="Отправьте Ф.И.О. сотрудника.", en="Send the employee full name."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(LocalizedTextFilter(*employee_list_button_texts()))
async def employee_list_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await _set_list_filters(state, EmployeeFiltersDTO())
    await _show_employee_list(message, EmployeeService(session), access.company.id, access.user.language, state)


@router.message(LocalizedTextFilter(*employee_search_button_texts()))
async def employee_search_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await state.set_state(EmployeeSearchStates.waiting_for_query)
    await message.answer(
        t(access.user.language, uz="Qidiruv matnini yuboring. F.I.Sh, kod yoki Telegram ID bo'yicha qidiriladi.", ru="Отправьте поисковый запрос. Поиск работает по Ф.И.О., коду или Telegram ID.", en="Send the search query. Search works by full name, code, or Telegram ID."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(LocalizedTextFilter(*employee_filters_button_texts()))
async def employee_filter_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    current_filters = await _get_list_filters(state)
    await state.clear()
    await _set_filter_draft(state, current_filters)
    await message.answer(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(current_filters, access.user.language),
    )


@router.message(
    EmployeeCreateStates.waiting_for_full_name,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_phone,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_telegram_id,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_employee_code,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_position,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_branch,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_department,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_shift,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_hire_date,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeCreateStates.waiting_for_confirmation,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeSearchStates.waiting_for_query,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    EmployeeEditStates.waiting_for_value,
    LocalizedTextFilter(*back_button_texts()),
)
async def employee_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_employee_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(EmployeeCreateStates.waiting_for_full_name)
async def employee_create_full_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    full_name = EmployeeService.normalize_text(message.text or "")
    if not full_name:
        await message.answer(t(access.user.language, uz="F.I.Sh bo'sh bo'lmasin.", ru="Ф.И.О. не должно быть пустым.", en="Full name cannot be empty."))
        return
    await state.update_data(full_name=full_name)
    await state.set_state(EmployeeCreateStates.waiting_for_phone)
    await message.answer(t(access.user.language, uz="Telefon raqamini yuboring yoki `-` yuboring.", ru="Отправьте номер телефона или `-`.", en="Send the phone number or `-`.")) 


@router.message(EmployeeCreateStates.waiting_for_phone)
async def employee_create_phone_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        phone = EmployeeService.parse_phone(message.text or "")
    except InvalidPhoneError:
        await message.answer(t(access.user.language, uz="Telefon raqami noto'g'ri.", ru="Некорректный номер телефона.", en="Invalid phone number."))
        return
    await state.update_data(phone=phone)
    await state.set_state(EmployeeCreateStates.waiting_for_telegram_id)
    await message.answer(t(access.user.language, uz="Telegram ID yuboring yoki `-` yuboring.", ru="Отправьте Telegram ID или `-`.", en="Send the Telegram ID or `-`.")) 


@router.message(EmployeeCreateStates.waiting_for_telegram_id)
async def employee_create_telegram_id_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        telegram_id = EmployeeService.parse_optional_telegram_id(message.text or "")
    except ValueError:
        await message.answer(t(access.user.language, uz="Telegram ID noto'g'ri.", ru="Некорректный Telegram ID.", en="Invalid Telegram ID."))
        return
    await state.update_data(telegram_id=telegram_id)
    await state.set_state(EmployeeCreateStates.waiting_for_employee_code)
    await message.answer(t(access.user.language, uz="Employee code yuboring yoki `-` yuboring.", ru="Отправьте код сотрудника или `-`.", en="Send the employee code or `-`.")) 


@router.message(EmployeeCreateStates.waiting_for_employee_code)
async def employee_create_code_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.update_data(employee_code=EmployeeService.normalize_text(message.text or "") or None)
    await state.set_state(EmployeeCreateStates.waiting_for_position)
    await message.answer(t(access.user.language, uz="Lavozimni yuboring yoki `-` yuboring.", ru="Отправьте должность или `-`.", en="Send the position or `-`.")) 


@router.message(EmployeeCreateStates.waiting_for_position)
async def employee_create_position_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    branches = await BranchService(session).list_branch_options(access.company.id, active_only=True)
    await state.update_data(position=EmployeeService.normalize_text(message.text or "") or None)
    await state.set_state(EmployeeCreateStates.waiting_for_branch)
    await message.answer(
        t(access.user.language, uz="Filialni tanlang.", ru="Выберите филиал.", en="Choose a branch."),
        reply_markup=build_option_selection_keyboard(
            [(branch.id, branch.name) for branch in branches],
            callback_prefix="employee:create_branch_select",
            language=access.user.language,
            back_callback="employee:create_branch_back",
        ),
    )


@router.callback_query(EmployeeCreateStates.waiting_for_branch, F.data.startswith("employee:create_branch_select:"))
async def employee_create_branch_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    branch_id = int(callback.data.rsplit(":", 1)[-1])
    departments = await DepartmentService(session).list_department_options(access.company.id, active_only=True)
    await state.update_data(branch_id=branch_id)
    await state.set_state(EmployeeCreateStates.waiting_for_department)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Bo'limni tanlang yoki o'tkazib yuboring.", ru="Выберите отдел или пропустите.", en="Choose a department or skip."),
        reply_markup=build_option_selection_keyboard(
            [(department.id, department.name) for department in departments],
            callback_prefix="employee:create_department_select",
            language=access.user.language,
            back_callback="employee:create_department_back",
            allow_skip=True,
        ),
    )


@router.callback_query(EmployeeCreateStates.waiting_for_branch, F.data == "employee:create_branch_back")
@router.callback_query(EmployeeCreateStates.waiting_for_department, F.data == "employee:create_department_back")
@router.callback_query(EmployeeCreateStates.waiting_for_shift, F.data == "employee:create_shift_back")
async def employee_create_selection_back_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(t(access.user.language, uz="Ishchi yaratish oynasi yopildi.", ru="Окно создания сотрудника закрыто.", en="Employee creation window was closed."))
    await show_employee_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(EmployeeCreateStates.waiting_for_department, F.data.startswith("employee:create_department_select:"))
async def employee_create_department_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    department_token = callback.data.rsplit(":", 1)[-1]
    department_id = None if department_token == "skip" else int(department_token)
    shifts = await ShiftService(session).list_shift_options(access.company.id, active_only=True)
    await state.update_data(department_id=department_id)
    await state.set_state(EmployeeCreateStates.waiting_for_shift)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Smenani tanlang yoki o'tkazib yuboring.", ru="Выберите смену или пропустите.", en="Choose a shift or skip."),
        reply_markup=build_option_selection_keyboard(
            [(shift.id, shift.name) for shift in shifts],
            callback_prefix="employee:create_shift_select",
            language=access.user.language,
            back_callback="employee:create_shift_back",
            allow_skip=True,
        ),
    )


@router.callback_query(EmployeeCreateStates.waiting_for_shift, F.data.startswith("employee:create_shift_select:"))
async def employee_create_shift_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    shift_token = callback.data.rsplit(":", 1)[-1]
    shift_id = None if shift_token == "skip" else int(shift_token)
    await state.update_data(shift_id=shift_id)
    await state.set_state(EmployeeCreateStates.waiting_for_hire_date)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishga kirgan sanani yuboring yoki `-` yuboring. Format: YYYY-MM-DD", ru="Отправьте дату найма или `-`. Формат: YYYY-MM-DD", en="Send the hire date or `-`. Format: YYYY-MM-DD"),
    )


@router.message(EmployeeCreateStates.waiting_for_hire_date)
async def employee_create_hire_date_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    try:
        hire_date = EmployeeService.parse_optional_date(message.text or "")
    except ValueError:
        await message.answer(t(access.user.language, uz="Sana noto'g'ri. Format YYYY-MM-DD bo'lsin.", ru="Некорректная дата. Используйте формат YYYY-MM-DD.", en="Invalid date. Use YYYY-MM-DD format."))
        return
    await state.update_data(hire_date=hire_date.isoformat() if hire_date else None)
    data = await state.get_data()
    await state.set_state(EmployeeCreateStates.waiting_for_confirmation)
    await message.answer(
        "\n".join(
            [
                t(access.user.language, uz="Yangi ishchini tasdiqlang.", ru="Подтвердите нового сотрудника.", en="Confirm the new employee."),
                t(access.user.language, uz=f"👤 F.I.Sh: {data.get('full_name', '-')}", ru=f"👤 Ф.И.О.: {data.get('full_name', '-')}", en=f"👤 Full name: {data.get('full_name', '-')}"),
                t(access.user.language, uz=f"📞 Telefon: {data.get('phone') or '-'}", ru=f"📞 Телефон: {data.get('phone') or '-'}", en=f"📞 Phone: {data.get('phone') or '-'}"),
                t(access.user.language, uz=f"🆔 Telegram ID: {data.get('telegram_id') or '-'}", ru=f"🆔 Telegram ID: {data.get('telegram_id') or '-'}", en=f"🆔 Telegram ID: {data.get('telegram_id') or '-'}"),
                t(access.user.language, uz=f"🏷 Kod: {data.get('employee_code') or '-'}", ru=f"🏷 Код: {data.get('employee_code') or '-'}", en=f"🏷 Code: {data.get('employee_code') or '-'}"),
                t(access.user.language, uz=f"💼 Lavozim: {data.get('position') or '-'}", ru=f"💼 Должность: {data.get('position') or '-'}", en=f"💼 Position: {data.get('position') or '-'}"),
                t(access.user.language, uz=f"📅 Sana: {data.get('hire_date') or '-'}", ru=f"📅 Дата: {data.get('hire_date') or '-'}", en=f"📅 Date: {data.get('hire_date') or '-'}"),
            ]
        ),
        reply_markup=build_confirmation_keyboard("employee:create:confirm", "employee:create:cancel", access.user.language),
    )


@router.message(EmployeeCreateStates.waiting_for_branch)
@router.message(EmployeeCreateStates.waiting_for_department)
@router.message(EmployeeCreateStates.waiting_for_shift)
async def employee_create_selection_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, tanlovni tugmalar orqali bajaring.", ru="Пожалуйста, сделайте выбор с помощью кнопок.", en="Please make the selection using the buttons."))


@router.message(EmployeeCreateStates.waiting_for_confirmation)
async def employee_create_waiting_confirmation_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, inline tasdiqlash tugmalaridan foydalaning.", ru="Пожалуйста, используйте inline-кнопки подтверждения.", en="Please use the inline confirmation buttons."))


@router.callback_query(EmployeeCreateStates.waiting_for_confirmation, F.data == "employee:create:confirm")
async def employee_create_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    service = EmployeeService(session)
    try:
        employee = await service.create_employee(
            access.company.id,
            EmployeeCreateDTO(
                full_name=str(data.get("full_name", "")),
                phone=data.get("phone") if isinstance(data.get("phone"), str) else None,
                telegram_id=data.get("telegram_id") if isinstance(data.get("telegram_id"), int) else None,
                employee_code=data.get("employee_code") if isinstance(data.get("employee_code"), str) else None,
                position=data.get("position") if isinstance(data.get("position"), str) else None,
                branch_id=int(data.get("branch_id")) if data.get("branch_id") is not None else None,
                department_id=int(data.get("department_id")) if data.get("department_id") is not None else None,
                shift_id=int(data.get("shift_id")) if data.get("shift_id") is not None else None,
                hire_date=EmployeeService.parse_optional_date(str(data.get("hire_date") or "-")),
            ),
            actor_telegram_id=access.user.telegram_id,
        )
    except (EmployeeAlreadyExistsError, BranchAssignmentRequiredError, BranchNotFoundError, ForeignEntityScopeError):
        await callback.answer(t(access.user.language, uz="Ishchini saqlashda xato yuz berdi. Kiritilgan ma'lumotlarni tekshiring.", ru="Ошибка при сохранении сотрудника. Проверьте введённые данные.", en="Could not save the employee. Check the entered data."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Ishchi yaratildi.", ru="Сотрудник создан.", en="Employee created."))
    await callback.message.edit_text(
        _format_employee_detail(access.user.language, employee),
        reply_markup=build_employee_detail_keyboard(employee, 1, access.user.language),
    )


@router.callback_query(EmployeeCreateStates.waiting_for_confirmation, F.data == "employee:create:cancel")
async def employee_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(t(access.user.language, uz="Ishchi yaratish bekor qilindi.", ru="Создание сотрудника отменено.", en="Employee creation cancelled."))
    await show_employee_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.message(EmployeeSearchStates.waiting_for_query)
async def employee_search_query_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    filters = EmployeeFiltersDTO(search=EmployeeService.normalize_search_query(message.text or ""))
    await state.clear()
    await _set_list_filters(state, filters)
    await _show_employee_list(message, EmployeeService(session), access.company.id, access.user.language, state)


@router.callback_query(F.data == "employee:noop")
async def employee_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("employee:list:"))
async def employee_list_callback_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    page = int(callback.data.rsplit(":", 1)[-1])
    filters = await _get_list_filters(state)
    employee_page = await EmployeeService(session).list_employees(access.company.id, page=page, page_size=EMPLOYEE_PAGE_SIZE, filters=filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz=f"Ishchilar ro'yxati ({employee_page.page}/{employee_page.total_pages})", ru=f"Список сотрудников ({employee_page.page}/{employee_page.total_pages})", en=f"Employee list ({employee_page.page}/{employee_page.total_pages})"),
        reply_markup=build_employee_list_keyboard(employee_page, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:detail:"))
async def employee_detail_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    try:
        employee = await EmployeeService(session).get_employee_detail(access.company.id, int(employee_id_raw))
    except EmployeeNotFoundError:
        await callback.answer(t(access.user.language, uz="Ishchi topilmadi.", ru="Сотрудник не найден.", en="Employee not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_employee_detail(access.user.language, employee),
        reply_markup=build_employee_detail_keyboard(employee, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("employee:toggle:"))
async def employee_toggle_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    employee = await EmployeeService(session).toggle_employee_status(access.company.id, int(employee_id_raw), actor_telegram_id=access.user.telegram_id)
    await callback.answer()
    await callback.message.edit_text(
        _format_employee_detail(access.user.language, employee),
        reply_markup=build_employee_detail_keyboard(employee, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("employee:edit_menu:"))
async def employee_edit_menu_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Tahrirlanadigan maydonni tanlang.", ru="Выберите поле для редактирования.", en="Choose the field to edit."),
        reply_markup=build_employee_edit_menu_keyboard(int(employee_id_raw), int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("employee:edit_field:"))
async def employee_edit_field_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw, field = callback.data.split(":", 4)
    await state.clear()
    await state.update_data(employee_id=int(employee_id_raw), page=int(page_raw), field=field)
    await state.set_state(EmployeeEditStates.waiting_for_value)
    await callback.answer()
    await callback.message.answer(
        t(access.user.language, uz="Yangi qiymatni yuboring. Tozalash uchun `-` yuboring.", ru="Отправьте новое значение. Для очистки отправьте `-`.", en="Send the new value. Send `-` to clear it."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(EmployeeEditStates.waiting_for_value)
async def employee_edit_value_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    data = await state.get_data()
    employee_id = int(data.get("employee_id", 0))
    page = int(data.get("page", 1))
    field = str(data.get("field", ""))
    service = EmployeeService(session)
    employee = await service.get_employee_detail(access.company.id, employee_id)

    try:
        if field == "full_name":
            payload = _build_update_payload(employee, full_name=message.text or "")
        elif field == "phone":
            payload = _build_update_payload(employee, phone=EmployeeService.parse_phone(message.text or ""))
        elif field == "telegram_id":
            payload = _build_update_payload(employee, telegram_id=EmployeeService.parse_optional_telegram_id(message.text or ""))
        elif field == "employee_code":
            code = EmployeeService.normalize_text(message.text or "")
            payload = _build_update_payload(employee, employee_code=code or None)
        elif field == "position":
            position = EmployeeService.normalize_text(message.text or "")
            payload = _build_update_payload(employee, position=position or None)
        elif field == "hire_date":
            payload = _build_update_payload(employee, hire_date=EmployeeService.parse_optional_date(message.text or ""))
        else:
            await message.answer(t(access.user.language, uz="Noma'lum maydon.", ru="Неизвестное поле.", en="Unknown field."))
            return
        updated_employee = await service.update_employee(access.company.id, employee_id, payload, actor_telegram_id=access.user.telegram_id)
    except (InvalidPhoneError, ValueError):
        await message.answer(t(access.user.language, uz="Qiymat noto'g'ri.", ru="Некорректное значение.", en="Invalid value."))
        return
    except EmployeeAlreadyExistsError:
        await message.answer(t(access.user.language, uz="Bunday employee code allaqachon mavjud.", ru="Такой код сотрудника уже существует.", en="This employee code already exists."))
        return

    await state.clear()
    await message.answer(
        _format_employee_detail(access.user.language, updated_employee),
        reply_markup=build_employee_detail_keyboard(updated_employee, page, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:assignments:"))
async def employee_assignments_menu_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Qaysi biriktirishni o'zgartirmoqchisiz?", ru="Какую привязку хотите изменить?", en="Which assignment do you want to update?"),
        reply_markup=build_employee_assignment_keyboard(int(employee_id_raw), int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("employee:assign_branch:"))
async def employee_assign_branch_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    options = await BranchService(session).list_branch_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Yangi filialni tanlang.", ru="Выберите новый филиал.", en="Choose the new branch."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix=f"employee:assign_branch_select:{employee_id_raw}:{page_raw}",
            language=access.user.language,
            back_callback=f"employee:assignments:{employee_id_raw}:{page_raw}",
        ),
    )


@router.callback_query(F.data.startswith("employee:assign_department:"))
async def employee_assign_department_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    options = await DepartmentService(session).list_department_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Yangi bo'limni tanlang.", ru="Выберите новый отдел.", en="Choose the new department."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix=f"employee:assign_department_select:{employee_id_raw}:{page_raw}",
            language=access.user.language,
            back_callback=f"employee:assignments:{employee_id_raw}:{page_raw}",
            allow_clear=True,
        ),
    )


@router.callback_query(F.data.startswith("employee:assign_shift:"))
async def employee_assign_shift_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, employee_id_raw, page_raw = callback.data.split(":", 3)
    options = await ShiftService(session).list_shift_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Yangi smenani tanlang.", ru="Выберите новую смену.", en="Choose the new shift."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix=f"employee:assign_shift_select:{employee_id_raw}:{page_raw}",
            language=access.user.language,
            back_callback=f"employee:assignments:{employee_id_raw}:{page_raw}",
            allow_clear=True,
        ),
    )


async def _update_employee_assignment(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    *,
    employee_id: int,
    page: int,
    changes: dict[str, object],
) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    service = EmployeeService(session)
    try:
        employee = await service.get_employee_detail(access.company.id, employee_id)
        updated_employee = await service.update_employee(
            access.company.id,
            employee_id,
            _build_update_payload(employee, **changes),
            actor_telegram_id=access.user.telegram_id,
        )
    except (EmployeeNotFoundError, BranchNotFoundError, ForeignEntityScopeError, BranchAssignmentRequiredError):
        await callback.answer(
            t(access.user.language, uz="Biriktirishni yangilab bo'lmadi.", ru="Не удалось обновить привязку.", en="Could not update the assignment."),
            show_alert=True,
        )
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_employee_detail(access.user.language, updated_employee),
        reply_markup=build_employee_detail_keyboard(updated_employee, page, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:assign_branch_select:"))
async def employee_assign_branch_select_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if callback.data is None:
        return
    _, _, _, employee_id_raw, page_raw, branch_id_raw = callback.data.split(":", 5)
    await _update_employee_assignment(
        callback,
        session,
        settings,
        employee_id=int(employee_id_raw),
        page=int(page_raw),
        changes={"branch_id": int(branch_id_raw)},
    )


@router.callback_query(F.data.startswith("employee:assign_department_select:"))
async def employee_assign_department_select_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if callback.data is None:
        return
    _, _, _, employee_id_raw, page_raw, value_raw = callback.data.split(":", 5)
    await _update_employee_assignment(
        callback,
        session,
        settings,
        employee_id=int(employee_id_raw),
        page=int(page_raw),
        changes={"department_id": None if value_raw == "clear" else int(value_raw)},
    )


@router.callback_query(F.data.startswith("employee:assign_shift_select:"))
async def employee_assign_shift_select_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if callback.data is None:
        return
    _, _, _, employee_id_raw, page_raw, value_raw = callback.data.split(":", 5)
    await _update_employee_assignment(
        callback,
        session,
        settings,
        employee_id=int(employee_id_raw),
        page=int(page_raw),
        changes={"shift_id": None if value_raw == "clear" else int(value_raw)},
    )


@router.callback_query(F.data.startswith("employee:filter:status:"))
async def employee_filter_status_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    value = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    filters = EmployeeFiltersDTO(
        search=filters.search,
        is_active=True if value == "active" else False if value == "inactive" else None,
        branch_id=filters.branch_id,
        department_id=filters.department_id,
        shift_id=filters.shift_id,
    )
    await _set_filter_draft(state, filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )


@router.callback_query(F.data == "employee:filter:clear")
async def employee_filter_clear_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    filters = EmployeeFiltersDTO()
    await _set_filter_draft(state, filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )


@router.callback_query(F.data == "employee:filter:apply")
async def employee_filter_apply_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    filters = await _get_filter_draft(state)
    await _set_list_filters(state, filters)
    employee_page = await EmployeeService(session).list_employees(access.company.id, page=1, page_size=EMPLOYEE_PAGE_SIZE, filters=filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz=f"Ishchilar ro'yxati ({employee_page.page}/{employee_page.total_pages})", ru=f"Список сотрудников ({employee_page.page}/{employee_page.total_pages})", en=f"Employee list ({employee_page.page}/{employee_page.total_pages})"),
        reply_markup=build_employee_list_keyboard(employee_page, access.user.language),
    )


@router.callback_query(F.data == "employee:filter_branch:open")
async def employee_filter_branch_open_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    options = await BranchService(session).list_branch_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Filial filterini tanlang.", ru="Выберите фильтр филиала.", en="Choose the branch filter."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix="employee:filter_branch_select",
            language=access.user.language,
            back_callback="employee:filter_back",
            allow_clear=True,
        ),
    )


@router.callback_query(F.data == "employee:filter_department:open")
async def employee_filter_department_open_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    options = await DepartmentService(session).list_department_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Bo'lim filterini tanlang.", ru="Выберите фильтр отдела.", en="Choose the department filter."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix="employee:filter_department_select",
            language=access.user.language,
            back_callback="employee:filter_back",
            allow_clear=True,
        ),
    )


@router.callback_query(F.data == "employee:filter_shift:open")
async def employee_filter_shift_open_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    options = await ShiftService(session).list_shift_options(access.company.id, active_only=True)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Smena filterini tanlang.", ru="Выберите фильтр смены.", en="Choose the shift filter."),
        reply_markup=build_option_selection_keyboard(
            [(item.id, item.name) for item in options],
            callback_prefix="employee:filter_shift_select",
            language=access.user.language,
            back_callback="employee:filter_back",
            allow_clear=True,
        ),
    )


@router.callback_query(F.data == "employee:filter_back")
async def employee_filter_back_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    filters = await _get_filter_draft(state)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:filter_branch_select:"))
async def employee_filter_branch_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    value = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    filters = EmployeeFiltersDTO(
        search=filters.search,
        is_active=filters.is_active,
        branch_id=None if value == "clear" else int(value),
        department_id=filters.department_id,
        shift_id=filters.shift_id,
    )
    await _set_filter_draft(state, filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:filter_department_select:"))
async def employee_filter_department_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    value = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    filters = EmployeeFiltersDTO(
        search=filters.search,
        is_active=filters.is_active,
        branch_id=filters.branch_id,
        department_id=None if value == "clear" else int(value),
        shift_id=filters.shift_id,
    )
    await _set_filter_draft(state, filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )


@router.callback_query(F.data.startswith("employee:filter_shift_select:"))
async def employee_filter_shift_select_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    value = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    filters = EmployeeFiltersDTO(
        search=filters.search,
        is_active=filters.is_active,
        branch_id=filters.branch_id,
        department_id=filters.department_id,
        shift_id=None if value == "clear" else int(value),
    )
    await _set_filter_draft(state, filters)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Ishchilar filterlari", ru="Фильтры сотрудников", en="Employee filters"),
        reply_markup=build_employee_filter_keyboard(filters, access.user.language),
    )
