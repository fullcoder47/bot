from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.role import RoleFilter
from app.bot.filters.text import LocalizedTextFilter
from app.bot.keyboards.inline.company import (
    build_company_action_confirmation_keyboard,
    build_company_create_plan_keyboard,
    build_company_delete_confirmation_keyboard,
    build_company_detail_keyboard,
    build_company_filter_keyboard,
    build_company_list_keyboard,
    build_company_plan_update_keyboard,
)
from app.bot.keyboards.reply.super_admin import build_super_admin_keyboard, companies_button_texts
from app.bot.keyboards.reply.super_admin_company import (
    add_company_button_texts,
    build_company_flow_back_keyboard,
    build_super_admin_company_keyboard,
    company_filters_button_texts,
    company_list_button_texts,
    company_menu_back_button_texts,
    company_search_button_texts,
)
from app.bot.states.company_states import (
    CompanyAdminAssignStates,
    CompanyCreateStates,
    CompanyDeleteStates,
    CompanyEditStates,
    CompanySearchStates,
    CompanySubscriptionStates,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import (
    CompanyAdminAssignDTO,
    CompanyCreateDTO,
    CompanyDetailDTO,
    CompanyListFiltersDTO,
    CompanyListPageDTO,
    CompanyUpdateDTO,
    SubscriptionUpdateDTO,
)
from app.domain.dto.user_dto import UserDTO
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.role import UserRole
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.exceptions.company_exceptions import (
    CompanyAdminAssignmentError,
    CompanyAlreadyExistsError,
    CompanyNameValidationError,
    CompanyNotFoundError,
    InvalidTelegramIdError,
)
from app.services.auth_service import AuthService
from app.services.company_admin_service import CompanyAdminService
from app.services.company_service import CompanyService

router = Router(name="company")
router.message.filter(RoleFilter(UserRole.SUPER_ADMIN))
router.callback_query.filter(RoleFilter(UserRole.SUPER_ADMIN))

COMPANY_PAGE_SIZE = CompanyService.DEFAULT_PAGE_SIZE
LIST_CONTEXT_KEY = "company_list_context"
FILTER_DRAFT_KEY = "company_filter_draft"
PRESERVED_CONTEXT_KEYS = (LIST_CONTEXT_KEY, FILTER_DRAFT_KEY)


def _default_list_context() -> dict[str, object]:
    return {
        "search": None,
        "filters": {
            "is_active": None,
            "plan": None,
            "expired_only": False,
        },
    }


def _serialize_filters(filters: CompanyListFiltersDTO) -> dict[str, object]:
    return {
        "is_active": filters.is_active,
        "plan": filters.plan.value if filters.plan else None,
        "expired_only": filters.expired_only,
    }


def _deserialize_filters(raw_filters: dict[str, object] | None) -> CompanyListFiltersDTO:
    raw_filters = raw_filters or {}
    plan_raw = raw_filters.get("plan")
    plan = CompanyPlan(plan_raw) if isinstance(plan_raw, str) and plan_raw else None
    is_active = raw_filters.get("is_active")
    if not isinstance(is_active, bool):
        is_active = None

    return CompanyListFiltersDTO(
        is_active=is_active,
        plan=plan,
        expired_only=bool(raw_filters.get("expired_only", False)),
    )


def _has_active_filters(filters: CompanyListFiltersDTO) -> bool:
    return filters.is_active is not None or filters.plan is not None or filters.expired_only


def _extract_company_id_page(callback_data: str) -> tuple[int, int]:
    _, company_id_raw, page_raw = callback_data.rsplit(":", 2)
    return int(company_id_raw), int(page_raw)


def _extract_company_id_page_plan(callback_data: str) -> tuple[int, int, CompanyPlan]:
    _, company_id_raw, page_raw, plan_raw = callback_data.rsplit(":", 3)
    return int(company_id_raw), int(page_raw), CompanyPlan(plan_raw)


async def _get_preserved_data(state: FSMContext) -> dict[str, object]:
    data = await state.get_data()
    return {key: data[key] for key in PRESERVED_CONTEXT_KEYS if key in data}


async def _clear_flow_state_preserving_context(state: FSMContext) -> None:
    preserved = await _get_preserved_data(state)
    await state.clear()
    if preserved:
        await state.update_data(**preserved)


async def _set_flow_state(state: FSMContext, target_state, **extra_data: object) -> None:
    preserved = await _get_preserved_data(state)
    await state.clear()
    await state.update_data(**preserved, **extra_data)
    await state.set_state(target_state)


async def _get_list_context(state: FSMContext) -> dict[str, object]:
    data = await state.get_data()
    raw_context = data.get(LIST_CONTEXT_KEY)
    if not isinstance(raw_context, dict):
        return _default_list_context()

    raw_filters = raw_context.get("filters")
    if not isinstance(raw_filters, dict):
        raw_filters = _default_list_context()["filters"]

    search = raw_context.get("search")
    return {
        "search": search if isinstance(search, str) and search else None,
        "filters": {
            "is_active": raw_filters.get("is_active"),
            "plan": raw_filters.get("plan"),
            "expired_only": bool(raw_filters.get("expired_only", False)),
        },
    }


async def _set_list_context(
    state: FSMContext,
    *,
    search: str | None,
    filters: CompanyListFiltersDTO,
) -> None:
    normalized_search = CompanyService.normalize_search_query(search or "") or None
    await state.update_data(
        **{
            LIST_CONTEXT_KEY: {
                "search": normalized_search,
                "filters": _serialize_filters(filters),
            }
        }
    )


async def _get_filter_draft(state: FSMContext) -> CompanyListFiltersDTO:
    data = await state.get_data()
    raw_filters = data.get(FILTER_DRAFT_KEY)
    if not isinstance(raw_filters, dict):
        context = await _get_list_context(state)
        return _deserialize_filters(context.get("filters") if isinstance(context.get("filters"), dict) else None)

    return _deserialize_filters(raw_filters)


async def _set_filter_draft(state: FSMContext, filters: CompanyListFiltersDTO) -> None:
    await state.update_data(**{FILTER_DRAFT_KEY: _serialize_filters(filters)})


def _format_filter_summary(language, filters: CompanyListFiltersDTO) -> str:
    parts: list[str] = []
    if filters.is_active is True:
        parts.append(t(language, uz="faol", ru="активные", en="active"))
    elif filters.is_active is False:
        parts.append(t(language, uz="nofaol", ru="неактивные", en="inactive"))
    if filters.plan is not None:
        parts.append(filters.plan.value)
    if filters.expired_only:
        parts.append(t(language, uz="muddati tugaganlar", ru="истекшие", en="expired"))
    return ", ".join(parts) if parts else t(language, uz="yo'q", ru="нет", en="none")


def _format_company_list_text(
    language,
    company_page: CompanyListPageDTO,
    search_query: str | None,
    filters: CompanyListFiltersDTO,
) -> str:
    lines = [
        t(
            language,
            uz=f"Kompaniyalar ro'yxati ({company_page.page}/{company_page.total_pages})",
            ru=f"Список компаний ({company_page.page}/{company_page.total_pages})",
            en=f"Company list ({company_page.page}/{company_page.total_pages})",
        ),
        t(
            language,
            uz=f"Natijalar soni: {company_page.total_items}",
            ru=f"Количество результатов: {company_page.total_items}",
            en=f"Results count: {company_page.total_items}",
        ),
    ]
    if search_query:
        lines.append(t(language, uz=f"Qidiruv: {search_query}", ru=f"Поиск: {search_query}", en=f"Search: {search_query}"))
    if _has_active_filters(filters):
        lines.append(
            t(
                language,
                uz=f"Filterlar: {_format_filter_summary(language, filters)}",
                ru=f"Фильтры: {_format_filter_summary(language, filters)}",
                en=f"Filters: {_format_filter_summary(language, filters)}",
            )
        )
    if not company_page.items:
        lines.append(
            t(
                language,
                uz="Mos kompaniyalar topilmadi.",
                ru="Подходящие компании не найдены.",
                en="No matching companies were found.",
            )
        )
    return "\n".join(lines)


def _format_company_detail(language, company: CompanyDetailDTO) -> str:
    status_text = t(language, uz="Faol" if company.is_active else "Nofaol", ru="Активна" if company.is_active else "Неактивна", en="Active" if company.is_active else "Inactive")
    assignment_text = (
        str(company.assigned_admin_telegram_id)
        if company.assigned_admin_telegram_id is not None
        else t(language, uz="Biriktirilmagan", ru="Не назначен", en="Not assigned")
    )
    assignment_status = (
        t(language, uz="Faol", ru="Активна", en="Active")
        if company.admin_assignment_is_active
        else t(language, uz="Nofaol", ru="Неактивна", en="Inactive")
        if company.has_admin_assignment
        else "-"
    )
    subscription_text = company.subscription_end.strftime("%Y-%m-%d") if company.subscription_end is not None else t(language, uz="Belgilanmagan", ru="Не указана", en="Not set")
    if company.subscription_end is not None and company.subscription_end.date() < datetime.utcnow().date():
        subscription_text = t(language, uz=f"{subscription_text} (muddati tugagan)", ru=f"{subscription_text} (истекла)", en=f"{subscription_text} (expired)")
    return "\n".join(
        [
            t(language, uz=f"🏢 Kompaniya: {company.name}", ru=f"🏢 Компания: {company.name}", en=f"🏢 Company: {company.name}"),
            t(language, uz=f"💳 Tarif: {company.plan.value}", ru=f"💳 Тариф: {company.plan.value}", en=f"💳 Plan: {company.plan.value}"),
            t(language, uz=f"🔁 Holati: {status_text}", ru=f"🔁 Статус: {status_text}", en=f"🔁 Status: {status_text}"),
            t(language, uz=f"📅 Subscription: {subscription_text}", ru=f"📅 Подписка: {subscription_text}", en=f"📅 Subscription: {subscription_text}"),
            t(language, uz=f"👤 Company admin: {assignment_text}", ru=f"👤 Company admin: {assignment_text}", en=f"👤 Company admin: {assignment_text}"),
            t(language, uz=f"🪪 Admin holati: {assignment_status}", ru=f"🪪 Статус админа: {assignment_status}", en=f"🪪 Admin status: {assignment_status}"),
        ]
    )


def _format_filter_menu_text(language, filters: CompanyListFiltersDTO) -> str:
    return "\n".join(
        [
            t(language, uz="Kompaniyalar filterlari", ru="Фильтры компаний", en="Company filters"),
            t(
                language,
                uz=f"Joriy tanlov: {_format_filter_summary(language, filters)}",
                ru=f"Текущий выбор: {_format_filter_summary(language, filters)}",
                en=f"Current selection: {_format_filter_summary(language, filters)}",
            ),
        ]
    )


async def _require_super_admin_message(message: Message, session: AsyncSession, settings: Settings) -> UserDTO | None:
    if message.from_user is None:
        return None
    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_super_admin(message.from_user.id)
    except LanguageSelectionRequiredError:
        await message.answer(t(DEFAULT_LANGUAGE, uz="Avval /start buyrug'ini yuboring.", ru="Сначала отправьте команду /start.", en="Please send /start first."))
    except AccessDeniedError as exc:
        await message.answer(t(exc.language or DEFAULT_LANGUAGE, uz="Sizda bu bo'limga kirish huquqi yo'q.", ru="У вас нет доступа к этому разделу.", en="You do not have access to this section."))
    return None


async def _require_super_admin_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> UserDTO | None:
    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_super_admin(callback.from_user.id)
    except LanguageSelectionRequiredError:
        await callback.answer(t(DEFAULT_LANGUAGE, uz="Avval /start buyrug'ini yuboring.", ru="Сначала отправьте команду /start.", en="Please send /start first."), show_alert=True)
    except AccessDeniedError as exc:
        await callback.answer(t(exc.language or DEFAULT_LANGUAGE, uz="Sizda bu bo'limga kirish huquqi yo'q.", ru="У вас нет доступа к этому разделу.", en="You do not have access to this section."), show_alert=True)
    return None


async def _show_company_menu(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Kompaniyalar menyusi", ru="Меню компаний", en="Companies menu"),
        reply_markup=build_super_admin_company_keyboard(language),
    )


async def _show_super_admin_panel(message: Message, language) -> None:
    await message.answer(
        t(language, uz="Super admin paneliga qaytdingiz.", ru="Вы вернулись в панель супер-админа.", en="You are back in the super admin panel."),
        reply_markup=build_super_admin_keyboard(language or DEFAULT_LANGUAGE),
    )


async def _load_company_page(session: AsyncSession, state: FSMContext, page: int) -> tuple[CompanyListPageDTO, str | None, CompanyListFiltersDTO]:
    context = await _get_list_context(state)
    filters = _deserialize_filters(context.get("filters") if isinstance(context.get("filters"), dict) else None)
    search_query = context.get("search")
    normalized_search = search_query if isinstance(search_query, str) and search_query else None
    company_service = CompanyService(session)
    if normalized_search:
        company_page = await company_service.search_companies(normalized_search, page=page, page_size=COMPANY_PAGE_SIZE, filters=filters)
    else:
        company_page = await company_service.list_companies(page=page, page_size=COMPANY_PAGE_SIZE, filters=filters)
    await _set_list_context(state, search=normalized_search, filters=filters)
    return company_page, normalized_search, filters


async def _answer_company_list_message(message: Message, session: AsyncSession, state: FSMContext, language, page: int = 1) -> None:
    company_page, search_query, filters = await _load_company_page(session, state, page)
    await message.answer(
        _format_company_list_text(language, company_page, search_query, filters),
        reply_markup=build_company_list_keyboard(company_page, language),
    )


async def _edit_company_list_message(message: Message, session: AsyncSession, state: FSMContext, language, page: int = 1) -> None:
    company_page, search_query, filters = await _load_company_page(session, state, page)
    await message.edit_text(
        _format_company_list_text(language, company_page, search_query, filters),
        reply_markup=build_company_list_keyboard(company_page, language),
    )


async def _show_company_detail_message(message: Message, session: AsyncSession, language, company_id: int, page: int) -> None:
    company = await CompanyService(session).get_company_detail(company_id)
    await message.answer(
        _format_company_detail(language, company),
        reply_markup=build_company_detail_keyboard(company, page, language),
    )


@router.message(CompanyCreateStates.waiting_for_name, LocalizedTextFilter(*company_menu_back_button_texts()))
async def create_company_name_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _clear_flow_state_preserving_context(state)
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyCreateStates.waiting_for_name)
async def create_company_name_input_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    company_service = CompanyService(session)
    try:
        company_name = await company_service.validate_new_company_name(message.text or "")
    except CompanyNameValidationError:
        await message.answer(t(user.language, uz="Kompaniya nomi bo'sh bo'lmasin. Qayta kiriting.", ru="Название компании не должно быть пустым. Введите снова.", en="Company name cannot be empty. Please enter it again."))
        return
    except CompanyAlreadyExistsError:
        await message.answer(t(user.language, uz="Bunday kompaniya allaqachon mavjud. Boshqa nom kiriting.", ru="Такая компания уже существует. Введите другое название.", en="This company already exists. Please enter another name."))
        return

    await state.update_data(company_name=company_name)
    await state.set_state(CompanyCreateStates.waiting_for_plan)
    await message.answer(
        t(user.language, uz="Endi kompaniya tarifini tanlang.", ru="Теперь выберите тариф компании.", en="Now choose the company plan."),
        reply_markup=build_company_create_plan_keyboard(user.language),
    )


@router.message(CompanyCreateStates.waiting_for_plan)
async def create_company_waiting_for_plan_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await message.answer(
        t(user.language, uz="Iltimos, tarifni inline tugmalar orqali tanlang.", ru="Пожалуйста, выберите тариф через inline-кнопки.", en="Please choose the plan using the inline buttons."),
        reply_markup=build_company_create_plan_keyboard(user.language),
    )


@router.message(CompanyCreateStates.waiting_for_confirmation)
async def create_company_confirmation_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await message.answer(
        t(user.language, uz="Iltimos, yaratishni inline tugmalar orqali tasdiqlang.", ru="Пожалуйста, подтвердите создание через inline-кнопки.", en="Please confirm the creation using the inline buttons.")
    )


@router.message(CompanyEditStates.waiting_for_name, LocalizedTextFilter(*company_menu_back_button_texts()))
async def edit_company_name_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    if company_id:
        try:
            await _show_company_detail_message(message, session, user.language, company_id, page)
        except CompanyNotFoundError:
            await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyEditStates.waiting_for_name)
async def edit_company_name_input_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    company_service = CompanyService(session)
    try:
        company = await company_service.get_company_detail(company_id)
        new_name = company_service.normalize_company_name(message.text or "")
        if not new_name:
            raise CompanyNameValidationError()
        await company_service.ensure_name_available(new_name, exclude_company_id=company_id)
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await message.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."))
        await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return
    except CompanyNameValidationError:
        await message.answer(t(user.language, uz="Kompaniya nomi bo'sh bo'lmasin. Qayta kiriting.", ru="Название компании не должно быть пустым. Введите снова.", en="Company name cannot be empty. Please enter it again."))
        return
    except CompanyAlreadyExistsError:
        await message.answer(t(user.language, uz="Bunday kompaniya allaqachon mavjud. Boshqa nom kiriting.", ru="Такая компания уже существует. Введите другое название.", en="This company already exists. Please enter another name."))
        return

    await state.update_data(new_company_name=new_name)
    await state.set_state(CompanyEditStates.waiting_for_confirmation)
    await message.answer(
        "\n".join(
            [
                t(user.language, uz="Kompaniya nomini yangilashni tasdiqlang.", ru="Подтвердите обновление названия компании.", en="Confirm the company rename."),
                t(user.language, uz=f"Joriy nom: {company.name}", ru=f"Текущее название: {company.name}", en=f"Current name: {company.name}"),
                t(user.language, uz=f"Yangi nom: {new_name}", ru=f"Новое название: {new_name}", en=f"New name: {new_name}"),
            ]
        ),
        reply_markup=build_company_action_confirmation_keyboard("company:edit_name:confirm", "company:edit_name:cancel", user.language),
    )


@router.message(CompanyEditStates.waiting_for_confirmation)
async def edit_company_confirmation_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await message.answer(
        t(user.language, uz="Iltimos, tahrirlashni inline tugmalar orqali tasdiqlang.", ru="Пожалуйста, подтвердите редактирование через inline-кнопки.", en="Please confirm the edit using the inline buttons.")
    )


@router.message(CompanyAdminAssignStates.waiting_for_telegram_id, LocalizedTextFilter(*company_menu_back_button_texts()))
async def assign_company_admin_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    if company_id:
        try:
            await _show_company_detail_message(message, session, user.language, company_id, page)
        except CompanyNotFoundError:
            await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyAdminAssignStates.waiting_for_telegram_id)
async def assign_company_admin_input_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    raw_telegram_id = (message.text or "").strip()
    if not raw_telegram_id.isdigit():
        await message.answer(t(user.language, uz="Telegram ID faqat raqam bo'lishi kerak. Qayta kiriting.", ru="Telegram ID должен состоять только из цифр. Введите снова.", en="Telegram ID must contain only digits. Please enter it again."))
        return

    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    company_service = CompanyService(session)
    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await message.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."))
        await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return

    telegram_id = int(raw_telegram_id)
    await state.update_data(assign_telegram_id=telegram_id)
    await state.set_state(CompanyAdminAssignStates.waiting_for_confirmation)
    await message.answer(
        "\n".join(
            [
                t(user.language, uz="Company admin biriktirishni tasdiqlang.", ru="Подтвердите назначение company admin.", en="Confirm the company admin assignment."),
                t(user.language, uz=f"Kompaniya: {company.name}", ru=f"Компания: {company.name}", en=f"Company: {company.name}"),
                t(user.language, uz=f"Telegram ID: {telegram_id}", ru=f"Telegram ID: {telegram_id}", en=f"Telegram ID: {telegram_id}"),
            ]
        ),
        reply_markup=build_company_action_confirmation_keyboard("company:assign:confirm", "company:assign:cancel", user.language),
    )


@router.message(CompanyAdminAssignStates.waiting_for_confirmation)
async def assign_company_admin_confirmation_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await message.answer(
        t(user.language, uz="Iltimos, admin biriktirishni inline tugmalar orqali tasdiqlang.", ru="Пожалуйста, подтвердите назначение через inline-кнопки.", en="Please confirm the assignment using the inline buttons.")
    )


@router.message(CompanySubscriptionStates.waiting_for_date, LocalizedTextFilter(*company_menu_back_button_texts()))
async def update_subscription_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    if company_id:
        try:
            await _show_company_detail_message(message, session, user.language, company_id, page)
        except CompanyNotFoundError:
            await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanySubscriptionStates.waiting_for_date)
async def update_subscription_input_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    raw_date = (message.text or "").strip()
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    try:
        company = await CompanyService(session).get_company_detail(company_id)
        subscription_end = CompanyService.parse_subscription_date(raw_date)
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await message.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."))
        await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return
    except ValueError:
        await message.answer(t(user.language, uz="Sana formati noto'g'ri. YYYY-MM-DD ko'rinishida yuboring.", ru="Некорректный формат даты. Отправьте в формате YYYY-MM-DD.", en="Invalid date format. Send it as YYYY-MM-DD."))
        return

    await state.update_data(subscription_end=subscription_end.isoformat(), subscription_date_text=raw_date)
    await state.set_state(CompanySubscriptionStates.waiting_for_confirmation)
    await message.answer(
        "\n".join(
            [
                t(user.language, uz="Subscription sanasini yangilashni tasdiqlang.", ru="Подтвердите обновление даты подписки.", en="Confirm the subscription update."),
                t(user.language, uz=f"Kompaniya: {company.name}", ru=f"Компания: {company.name}", en=f"Company: {company.name}"),
                t(user.language, uz=f"Yangi sana: {raw_date}", ru=f"Новая дата: {raw_date}", en=f"New date: {raw_date}"),
            ]
        ),
        reply_markup=build_company_action_confirmation_keyboard("company:subscription:confirm", "company:subscription:cancel", user.language),
    )


@router.message(CompanySubscriptionStates.waiting_for_confirmation)
async def update_subscription_confirmation_message_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await message.answer(
        t(user.language, uz="Iltimos, subscription yangilanishini inline tugmalar orqali tasdiqlang.", ru="Пожалуйста, подтвердите обновление подписки через inline-кнопки.", en="Please confirm the subscription update using the inline buttons.")
    )


@router.message(CompanySearchStates.waiting_for_query, LocalizedTextFilter(*company_menu_back_button_texts()))
async def search_company_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _clear_flow_state_preserving_context(state)
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanySearchStates.waiting_for_query)
async def search_company_query_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    search_query = CompanyService.normalize_search_query(message.text or "")
    if not search_query:
        await message.answer(t(user.language, uz="Qidiruv matni bo'sh bo'lmasin. Qayta kiriting.", ru="Поисковый запрос не должен быть пустым. Введите снова.", en="Search query cannot be empty. Please enter it again."))
        return

    current_context = await _get_list_context(state)
    filters = _deserialize_filters(current_context.get("filters") if isinstance(current_context.get("filters"), dict) else None)
    await _set_list_context(state, search=search_query, filters=filters)
    await _clear_flow_state_preserving_context(state)
    await _answer_company_list_message(message, session, state, user.language, page=1)


@router.message(StateFilter(None), LocalizedTextFilter(*companies_button_texts()))
async def companies_menu_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(StateFilter(None), LocalizedTextFilter(*add_company_button_texts()))
async def create_company_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _set_flow_state(state, CompanyCreateStates.waiting_for_name)
    await message.answer(
        t(user.language, uz="Yangi kompaniya nomini yuboring.", ru="Отправьте название новой компании.", en="Send the new company name."),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.message(StateFilter(None), LocalizedTextFilter(*company_list_button_texts()))
async def company_list_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _set_list_context(state, search=None, filters=CompanyListFiltersDTO())
    await _answer_company_list_message(message, session, state, user.language, page=1)


@router.message(StateFilter(None), LocalizedTextFilter(*company_search_button_texts()))
async def company_search_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await _set_flow_state(state, CompanySearchStates.waiting_for_query)
    await message.answer(
        t(user.language, uz="Kompaniya nomi bo'yicha qidiruv matnini yuboring.", ru="Отправьте текст для поиска по названию компании.", en="Send the company name search query."),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.message(StateFilter(None), LocalizedTextFilter(*company_filters_button_texts()))
async def company_filters_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    current_context = await _get_list_context(state)
    filters = _deserialize_filters(current_context.get("filters") if isinstance(current_context.get("filters"), dict) else None)
    await _set_filter_draft(state, filters)
    await message.answer(_format_filter_menu_text(user.language, filters), reply_markup=build_company_filter_keyboard(filters, user.language))


@router.message(StateFilter(None), LocalizedTextFilter(*company_menu_back_button_texts()))
async def company_menu_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return
    await state.clear()
    await _show_super_admin_panel(message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(CompanyCreateStates.waiting_for_plan, F.data == "company:create:back")
async def create_company_plan_back_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    await state.set_state(CompanyCreateStates.waiting_for_name)
    await callback.answer()
    await callback.message.edit_text(t(user.language, uz="Kompaniya nomini yuboring.", ru="Отправьте название компании.", en="Send the company name."))


@router.callback_query(CompanyCreateStates.waiting_for_plan, F.data.startswith("company:create:plan:"))
async def create_company_plan_selected_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    try:
        plan = CompanyPlan(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer(t(user.language, uz="Noto'g'ri tarif tanlandi.", ru="Выбран некорректный тариф.", en="An invalid plan was selected."), show_alert=True)
        return

    data = await state.get_data()
    company_name = str(data.get("company_name", "")).strip()
    if not company_name:
        await state.set_state(CompanyCreateStates.waiting_for_name)
        await callback.answer(t(user.language, uz="Avval kompaniya nomini kiriting.", ru="Сначала введите название компании.", en="Please enter the company name first."), show_alert=True)
        await callback.message.edit_text(t(user.language, uz="Kompaniya nomini yuboring.", ru="Отправьте название компании.", en="Send the company name."))
        return

    await state.update_data(company_plan=plan.value)
    await state.set_state(CompanyCreateStates.waiting_for_confirmation)
    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                t(user.language, uz="Kompaniya yaratishni tasdiqlang.", ru="Подтвердите создание компании.", en="Confirm company creation."),
                t(user.language, uz=f"Nomi: {company_name}", ru=f"Название: {company_name}", en=f"Name: {company_name}"),
                t(user.language, uz=f"Tarif: {plan.value}", ru=f"Тариф: {plan.value}", en=f"Plan: {plan.value}"),
            ]
        ),
        reply_markup=build_company_action_confirmation_keyboard("company:create:confirm", "company:create:cancel", user.language),
    )


@router.callback_query(CompanyCreateStates.waiting_for_confirmation, F.data == "company:create:confirm")
async def create_company_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_name = str(data.get("company_name", "")).strip()
    plan_raw = str(data.get("company_plan", CompanyPlan.BASIC.value))
    plan = CompanyPlan(plan_raw) if plan_raw in CompanyPlan._value2member_map_ else CompanyPlan.BASIC
    company_service = CompanyService(session)
    try:
        company = await company_service.create_company(CompanyCreateDTO(name=company_name, plan=plan), actor_telegram_id=user.telegram_id)
    except CompanyNameValidationError:
        await state.set_state(CompanyCreateStates.waiting_for_name)
        await callback.answer(t(user.language, uz="Kompaniya nomi noto'g'ri.", ru="Некорректное название компании.", en="Invalid company name."), show_alert=True)
        return
    except CompanyAlreadyExistsError:
        await state.set_state(CompanyCreateStates.waiting_for_name)
        await callback.answer(t(user.language, uz="Bu nomdagi kompaniya allaqachon mavjud.", ru="Компания с таким названием уже существует.", en="A company with this name already exists."), show_alert=True)
        return

    await _set_list_context(state, search=None, filters=CompanyListFiltersDTO())
    await _clear_flow_state_preserving_context(state)
    await callback.answer(t(user.language, uz="Kompaniya yaratildi.", ru="Компания создана.", en="Company created."))
    await callback.message.edit_text(t(user.language, uz="Kompaniya muvaffaqiyatli yaratildi.", ru="Компания успешно создана.", en="The company has been created successfully."))
    await callback.message.answer(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, 1, user.language))


@router.callback_query(CompanyCreateStates.waiting_for_confirmation, F.data == "company:create:cancel")
async def create_company_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    await _clear_flow_state_preserving_context(state)
    await callback.answer()
    await callback.message.edit_text(t(user.language, uz="Kompaniya yaratish bekor qilindi.", ru="Создание компании отменено.", en="Company creation was cancelled."))
    await _show_company_menu(callback.message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(CompanyEditStates.waiting_for_confirmation, F.data == "company:edit_name:confirm")
async def edit_company_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    new_name = str(data.get("new_company_name", "")).strip()
    company_service = CompanyService(session)
    try:
        company = await company_service.update_company(company_id, CompanyUpdateDTO(name=new_name), actor_telegram_id=user.telegram_id)
    except CompanyNameValidationError:
        await state.set_state(CompanyEditStates.waiting_for_name)
        await callback.answer(t(user.language, uz="Kompaniya nomi noto'g'ri.", ru="Некорректное название компании.", en="Invalid company name."), show_alert=True)
        return
    except CompanyAlreadyExistsError:
        await state.set_state(CompanyEditStates.waiting_for_name)
        await callback.answer(t(user.language, uz="Bu nomdagi kompaniya allaqachon mavjud.", ru="Компания с таким названием уже существует.", en="A company with this name already exists."), show_alert=True)
        return
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return

    await _clear_flow_state_preserving_context(state)
    await callback.answer(t(user.language, uz="Kompaniya yangilandi.", ru="Компания обновлена.", en="Company updated."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(CompanyEditStates.waiting_for_confirmation, F.data == "company:edit_name:cancel")
async def edit_company_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(CompanyAdminAssignStates.waiting_for_confirmation, F.data == "company:assign:confirm")
async def assign_company_admin_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    telegram_id = int(data.get("assign_telegram_id", 0))
    company_admin_service = CompanyAdminService(session)
    try:
        company = await company_admin_service.assign_company_admin(CompanyAdminAssignDTO(company_id=company_id, telegram_id=telegram_id), actor_telegram_id=user.telegram_id)
    except InvalidTelegramIdError:
        await state.set_state(CompanyAdminAssignStates.waiting_for_telegram_id)
        await callback.answer(t(user.language, uz="Telegram ID noto'g'ri.", ru="Некорректный Telegram ID.", en="Invalid Telegram ID."), show_alert=True)
        return
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return

    await _clear_flow_state_preserving_context(state)
    await callback.answer(t(user.language, uz="Company admin muvaffaqiyatli biriktirildi.", ru="Company admin успешно назначен.", en="Company admin assigned successfully."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(CompanyAdminAssignStates.waiting_for_confirmation, F.data == "company:assign:cancel")
async def assign_company_admin_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(CompanySubscriptionStates.waiting_for_confirmation, F.data == "company:subscription:confirm")
async def update_subscription_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    subscription_end = datetime.fromisoformat(str(data.get("subscription_end", "")))
    company_service = CompanyService(session)
    try:
        company = await company_service.update_subscription(company_id, SubscriptionUpdateDTO(subscription_end=subscription_end), actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _clear_flow_state_preserving_context(state)
    await callback.answer(t(user.language, uz="Subscription sanasi yangilandi.", ru="Дата подписки обновлена.", en="Subscription date updated."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(CompanySubscriptionStates.waiting_for_confirmation, F.data == "company:subscription:cancel")
async def update_subscription_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await _clear_flow_state_preserving_context(state)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data == "company:noop")
async def company_noop_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "company:menu")
async def company_menu_callback_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    await _clear_flow_state_preserving_context(state)
    await callback.answer()
    await callback.message.edit_text(t(user.language, uz="Kompaniyalar menyusiga qayting va kerakli bo'limni tanlang.", ru="Вернитесь в меню компаний и выберите нужный раздел.", en="Return to the companies menu and choose the required section."))
    await _show_company_menu(callback.message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data.startswith("company:list:"))
async def company_list_callback_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    page = int(callback.data.rsplit(":", 1)[-1])
    await _clear_flow_state_preserving_context(state)
    await callback.answer()
    await _edit_company_list_message(callback.message, session, state, user.language, page=page)


@router.callback_query(F.data.startswith("company:detail:"))
async def company_detail_callback_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:toggle:"))
async def toggle_company_status_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    company_service = CompanyService(session)
    try:
        company = await company_service.toggle_company_status(company_id, actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer(t(user.language, uz="Kompaniya holati yangilandi.", ru="Статус компании обновлен.", en="Company status updated."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:plan_menu:"))
async def plan_update_menu_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "\n".join([_format_company_detail(user.language, company), "", t(user.language, uz="Yangi tarifni tanlang.", ru="Выберите новый тариф.", en="Choose a new plan.")]),
        reply_markup=build_company_plan_update_keyboard(company_id, page, user.language),
    )


@router.callback_query(F.data.startswith("company:plan_select:"))
async def plan_update_selected_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    try:
        company_id, page, plan = _extract_company_id_page_plan(callback.data)
    except ValueError:
        await callback.answer(t(user.language, uz="Noto'g'ri tarif tanlandi.", ru="Выбран некорректный тариф.", en="An invalid plan was selected."), show_alert=True)
        return
    company_service = CompanyService(session)
    try:
        company = await company_service.update_company(company_id, CompanyUpdateDTO(plan=plan), actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer(t(user.language, uz="Tarif yangilandi.", ru="Тариф обновлен.", en="Plan updated."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:subscription_entry:"))
async def subscription_update_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _set_flow_state(state, CompanySubscriptionStates.waiting_for_date, company_id=company_id, page=page)
    await callback.answer()
    await callback.message.answer(
        t(
            user.language,
            uz=f"Yangi subscription sanasini yuboring.\nJoriy sana: {company.subscription_end.strftime('%Y-%m-%d') if company.subscription_end else '-'}\nFormat: YYYY-MM-DD",
            ru=f"Отправьте новую дату подписки.\nТекущая дата: {company.subscription_end.strftime('%Y-%m-%d') if company.subscription_end else '-'}\nФормат: YYYY-MM-DD",
            en=f"Send the new subscription date.\nCurrent date: {company.subscription_end.strftime('%Y-%m-%d') if company.subscription_end else '-'}\nFormat: YYYY-MM-DD",
        ),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("company:assign_entry:"))
async def assign_company_admin_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _set_flow_state(state, CompanyAdminAssignStates.waiting_for_telegram_id, company_id=company_id, page=page)
    await callback.answer()
    await callback.message.answer(
        t(user.language, uz="Company admin uchun Telegram ID yuboring.", ru="Отправьте Telegram ID для company admin.", en="Send the Telegram ID for the company admin."),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("company:edit:"))
async def edit_company_name_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _set_flow_state(state, CompanyEditStates.waiting_for_name, company_id=company_id, page=page)
    await callback.answer()
    await callback.message.answer(
        t(
            user.language,
            uz=f"Yangi kompaniya nomini yuboring.\nJoriy nom: {company.name}",
            ru=f"Отправьте новое название компании.\nТекущее название: {company.name}",
            en=f"Send the new company name.\nCurrent name: {company.name}",
        ),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("company:admin_deactivate:"))
async def deactivate_company_admin_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    company_admin_service = CompanyAdminService(session)
    try:
        company = await company_admin_service.deactivate_company_admin(company_id, actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    except CompanyAdminAssignmentError:
        await callback.answer(t(user.language, uz="Faol company admin topilmadi.", ru="Активный company admin не найден.", en="No active company admin was found."), show_alert=True)
        return
    await callback.answer(t(user.language, uz="Company admin deaktiv qilindi.", ru="Company admin деактивирован.", en="Company admin has been deactivated."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:admin_remove:"))
async def remove_company_admin_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    if not company.has_admin_assignment:
        await callback.answer(t(user.language, uz="Bu kompaniyada admin biriktirilmagan.", ru="У этой компании нет назначенного админа.", en="This company does not have an assigned admin."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                _format_company_detail(user.language, company),
                "",
                t(user.language, uz="Rostdan ham company adminni olib tashlamoqchimisiz?", ru="Вы действительно хотите убрать company admin?", en="Do you really want to remove the company admin?"),
            ]
        ),
        reply_markup=build_company_action_confirmation_keyboard(
            f"company:admin_remove_confirm:{company_id}:{page}",
            f"company:admin_remove_cancel:{company_id}:{page}",
            user.language,
        ),
    )


@router.callback_query(F.data.startswith("company:admin_remove_confirm:"))
async def remove_company_admin_confirm_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    company_admin_service = CompanyAdminService(session)
    try:
        company = await company_admin_service.remove_company_admin(company_id, actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    except CompanyAdminAssignmentError:
        await callback.answer(t(user.language, uz="Company admin biriktirilmagan.", ru="Company admin не назначен.", en="Company admin is not assigned."), show_alert=True)
        return
    await callback.answer(t(user.language, uz="Company admin olib tashlandi.", ru="Company admin удален.", en="Company admin has been removed."))
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:admin_remove_cancel:"))
async def remove_company_admin_cancel_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data.startswith("company:delete:"))
async def delete_company_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _set_flow_state(state, CompanyDeleteStates.waiting_for_confirmation, company_id=company_id, page=page)
    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                _format_company_detail(user.language, company),
                "",
                t(user.language, uz="Rostdan ham bu kompaniyani o'chirmoqchimisiz?", ru="Вы действительно хотите удалить эту компанию?", en="Do you really want to delete this company?"),
            ]
        ),
        reply_markup=build_company_delete_confirmation_keyboard(company_id, page, user.language),
    )


@router.callback_query(CompanyDeleteStates.waiting_for_confirmation, F.data.startswith("company:delete_confirm:"))
async def delete_company_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    try:
        await CompanyService(session).delete_company(company_id, actor_telegram_id=user.telegram_id)
    except CompanyNotFoundError:
        await _clear_flow_state_preserving_context(state)
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await _clear_flow_state_preserving_context(state)
    await callback.answer(t(user.language, uz="Kompaniya o'chirildi.", ru="Компания удалена.", en="Company deleted."))
    await _edit_company_list_message(callback.message, session, state, user.language, page=page)


@router.callback_query(CompanyDeleteStates.waiting_for_confirmation, F.data.startswith("company:delete_cancel:"))
async def delete_company_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    company_id, page = _extract_company_id_page(callback.data)
    await _clear_flow_state_preserving_context(state)
    try:
        company = await CompanyService(session).get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(t(user.language, uz="Kompaniya topilmadi.", ru="Компания не найдена.", en="Company not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_format_company_detail(user.language, company), reply_markup=build_company_detail_keyboard(company, page, user.language))


@router.callback_query(F.data == "company:filter:back")
async def filter_back_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    await callback.answer()
    await callback.message.edit_text(t(user.language, uz="Filter oynasi yopildi.", ru="Окно фильтров закрыто.", en="The filter window was closed."))


@router.callback_query(F.data == "company:filter:clear")
async def filter_clear_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    filters = CompanyListFiltersDTO()
    await _set_filter_draft(state, filters)
    await callback.answer(t(user.language, uz="Filterlar tozalandi.", ru="Фильтры сброшены.", en="Filters cleared."))
    await callback.message.edit_text(_format_filter_menu_text(user.language, filters), reply_markup=build_company_filter_keyboard(filters, user.language))


@router.callback_query(F.data == "company:filter:apply")
async def filter_apply_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return
    current_context = await _get_list_context(state)
    search_query = current_context.get("search")
    filters = await _get_filter_draft(state)
    await _set_list_context(state, search=search_query if isinstance(search_query, str) else None, filters=filters)
    await callback.answer(t(user.language, uz="Filterlar qo'llandi.", ru="Фильтры применены.", en="Filters applied."))
    await _edit_company_list_message(callback.message, session, state, user.language, page=1)


@router.callback_query(F.data.startswith("company:filter:status:"))
async def filter_status_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    selection = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    updated_filters = CompanyListFiltersDTO(
        is_active=True if selection == "active" else False if selection == "inactive" else None,
        plan=filters.plan,
        expired_only=filters.expired_only,
    )
    await _set_filter_draft(state, updated_filters)
    await callback.answer()
    await callback.message.edit_text(_format_filter_menu_text(user.language, updated_filters), reply_markup=build_company_filter_keyboard(updated_filters, user.language))


@router.callback_query(F.data.startswith("company:filter:plan:"))
async def filter_plan_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    selection = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    plan = CompanyPlan(selection) if selection in CompanyPlan._value2member_map_ else None
    updated_filters = CompanyListFiltersDTO(is_active=filters.is_active, plan=plan, expired_only=filters.expired_only)
    await _set_filter_draft(state, updated_filters)
    await callback.answer()
    await callback.message.edit_text(_format_filter_menu_text(user.language, updated_filters), reply_markup=build_company_filter_keyboard(updated_filters, user.language))


@router.callback_query(F.data.startswith("company:filter:expired:"))
async def filter_expired_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return
    selection = callback.data.rsplit(":", 1)[-1]
    filters = await _get_filter_draft(state)
    updated_filters = CompanyListFiltersDTO(is_active=filters.is_active, plan=filters.plan, expired_only=selection == "on")
    await _set_filter_draft(state, updated_filters)
    await callback.answer()
    await callback.message.edit_text(_format_filter_menu_text(user.language, updated_filters), reply_markup=build_company_filter_keyboard(updated_filters, user.language))
