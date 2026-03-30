from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.keyboards.inline.company import (
    build_company_create_plan_keyboard,
    build_company_delete_confirmation_keyboard,
    build_company_detail_keyboard,
    build_company_edit_keyboard,
    build_company_edit_plan_keyboard,
    build_company_list_keyboard,
)
from app.bot.keyboards.reply.super_admin import build_super_admin_keyboard, companies_button_texts
from app.bot.keyboards.reply.super_admin_company import (
    add_company_button_texts,
    build_company_flow_back_keyboard,
    build_super_admin_company_keyboard,
    company_list_button_texts,
    company_menu_back_button_texts,
)
from app.bot.states.company_states import (
    CompanyAdminAssignStates,
    CompanyCreateStates,
    CompanyDeleteStates,
    CompanyEditStates,
)
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.company_dto import (
    CompanyAdminAssignDTO,
    CompanyCreateDTO,
    CompanyDetailDTO,
    CompanyListPageDTO,
    CompanyUpdateDTO,
)
from app.domain.dto.user_dto import UserDTO
from app.domain.enums.company_plan import CompanyPlan
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.exceptions.company_exceptions import (
    CompanyAlreadyExistsError,
    CompanyNameValidationError,
    CompanyNotFoundError,
    InvalidTelegramIdError,
)
from app.services.auth_service import AuthService
from app.services.company_admin_service import CompanyAdminService
from app.services.company_service import CompanyService

router = Router(name="company")

COMPANY_PAGE_SIZE = CompanyService.DEFAULT_PAGE_SIZE


def _format_company_list_text(language, company_page: CompanyListPageDTO) -> str:
    if not company_page.items:
        return t(
            language,
            uz="Hozircha kompaniyalar mavjud emas.",
            ru="Пока компаний нет.",
            en="There are no companies yet.",
        )

    return t(
        language,
        uz=f"Kompaniyalar ro'yxati ({company_page.page}/{company_page.total_pages})",
        ru=f"Список компаний ({company_page.page}/{company_page.total_pages})",
        en=f"Company list ({company_page.page}/{company_page.total_pages})",
    )


def _format_company_detail(language, company: CompanyDetailDTO) -> str:
    status_text = t(
        language,
        uz="Faol" if company.is_active else "Nofaol",
        ru="Актив" if company.is_active else "Неактив",
        en="Active" if company.is_active else "Inactive",
    )
    admin_text = (
        str(company.assigned_admin_telegram_id)
        if company.assigned_admin_telegram_id is not None
        else t(
            language,
            uz="Biriktirilmagan",
            ru="Не назначен",
            en="Not assigned",
        )
    )
    assignment_status_text = (
        t(language, uz="Faol", ru="Активна", en="Active")
        if company.admin_assignment_is_active
        else t(language, uz="Nofaol", ru="Неактивна", en="Inactive")
        if company.has_admin_assignment
        else "-"
    )
    subscription_text = (
        company.subscription_end.strftime("%Y-%m-%d %H:%M")
        if isinstance(company.subscription_end, datetime)
        else "-"
    )

    return "\n".join(
        [
            t(
                language,
                uz=f"🏢 Kompaniya: {company.name}",
                ru=f"🏢 Компания: {company.name}",
                en=f"🏢 Company: {company.name}",
            ),
            t(
                language,
                uz=f"📦 Tarif: {company.plan.value}",
                ru=f"📦 Тариф: {company.plan.value}",
                en=f"📦 Plan: {company.plan.value}",
            ),
            t(
                language,
                uz=f"🔁 Holati: {status_text}",
                ru=f"🔁 Статус: {status_text}",
                en=f"🔁 Status: {status_text}",
            ),
            t(
                language,
                uz=f"📅 Obuna tugashi: {subscription_text}",
                ru=f"📅 Окончание подписки: {subscription_text}",
                en=f"📅 Subscription end: {subscription_text}",
            ),
            t(
                language,
                uz=f"👤 Company admin: {admin_text}",
                ru=f"👤 Company admin: {admin_text}",
                en=f"👤 Company admin: {admin_text}",
            ),
            t(
                language,
                uz=f"🪪 Biriktirish holati: {assignment_status_text}",
                ru=f"🪪 Статус назначения: {assignment_status_text}",
                en=f"🪪 Assignment status: {assignment_status_text}",
            ),
        ]
    )


async def _require_super_admin_message(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> UserDTO | None:
    if message.from_user is None:
        return None

    auth_service = AuthService(session, settings)

    try:
        return await auth_service.require_super_admin(message.from_user.id)
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
                uz="Sizda bu bo'limga kirish huquqi yo'q.",
                ru="У вас нет доступа к этому разделу.",
                en="You do not have access to this section.",
            )
        )

    return None


async def _require_super_admin_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> UserDTO | None:
    auth_service = AuthService(session, settings)

    try:
        return await auth_service.require_super_admin(callback.from_user.id)
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
                uz="Sizda bu bo'limga kirish huquqi yo'q.",
                ru="У вас нет доступа к этому разделу.",
                en="You do not have access to this section.",
            ),
            show_alert=True,
        )

    return None


async def _show_company_menu(message: Message, language) -> None:
    await message.answer(
        t(
            language,
            uz="Kompaniyalar menyusi",
            ru="Меню компаний",
            en="Companies menu",
        ),
        reply_markup=build_super_admin_company_keyboard(language),
    )


async def _restore_company_menu(message: Message, language) -> None:
    await message.answer(
        t(
            language,
            uz="Kompaniyalar menyusiga qaytdingiz.",
            ru="Вы вернулись в меню компаний.",
            en="You are back in the companies menu.",
        ),
        reply_markup=build_super_admin_company_keyboard(language),
    )


async def _show_super_admin_panel(message: Message, language) -> None:
    await message.answer(
        t(
            language,
            uz="Super admin paneliga qaytdingiz.",
            ru="Вы вернулись в панель супер-админа.",
            en="You are back in the super admin panel.",
        ),
        reply_markup=build_super_admin_keyboard(language or DEFAULT_LANGUAGE),
    )


async def _answer_company_list_message(
    message: Message,
    session: AsyncSession,
    language,
    page: int = 1,
) -> None:
    company_service = CompanyService(session)
    company_page = await company_service.list_companies(page=page, page_size=COMPANY_PAGE_SIZE)
    await message.answer(
        _format_company_list_text(language, company_page),
        reply_markup=build_company_list_keyboard(company_page, language),
    )


async def _edit_company_list_message(
    message: Message,
    session: AsyncSession,
    language,
    page: int = 1,
) -> None:
    company_service = CompanyService(session)
    company_page = await company_service.list_companies(page=page, page_size=COMPANY_PAGE_SIZE)
    await message.edit_text(
        _format_company_list_text(language, company_page),
        reply_markup=build_company_list_keyboard(company_page, language),
    )


@router.message(
    CompanyCreateStates.waiting_for_name,
    LocalizedTextFilter(*company_menu_back_button_texts()),
)
async def create_company_name_back_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await state.clear()
    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyCreateStates.waiting_for_name)
async def create_company_name_input_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    company_service = CompanyService(session)

    try:
        company_name = await company_service.validate_new_company_name(message.text or "")
    except CompanyNameValidationError:
        await message.answer(
            t(
                user.language,
                uz="Kompaniya nomi bo'sh bo'lmasin. Qayta kiriting.",
                ru="Название компании не должно быть пустым. Введите снова.",
                en="Company name cannot be empty. Please enter it again.",
            )
        )
        return
    except CompanyAlreadyExistsError:
        await message.answer(
            t(
                user.language,
                uz="Bunday kompaniya allaqachon mavjud. Boshqa nom kiriting.",
                ru="Такая компания уже существует. Введите другое название.",
                en="This company already exists. Please enter another name.",
            )
        )
        return

    await state.update_data(company_name=company_name)
    await state.set_state(CompanyCreateStates.waiting_for_plan)
    await message.answer(
        t(
            user.language,
            uz="Endi kompaniya tarifini tanlang.",
            ru="Теперь выберите тариф компании.",
            en="Now choose the company plan.",
        ),
        reply_markup=build_company_create_plan_keyboard(user.language),
    )


@router.message(CompanyCreateStates.waiting_for_plan)
async def create_company_waiting_for_plan_message_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await message.answer(
        t(
            user.language,
            uz="Iltimos, tarifni tugmalar orqali tanlang.",
            ru="Пожалуйста, выберите тариф с помощью кнопок.",
            en="Please choose the plan using the buttons.",
        ),
        reply_markup=build_company_create_plan_keyboard(user.language),
    )


@router.message(
    CompanyEditStates.waiting_for_name,
    LocalizedTextFilter(*company_menu_back_button_texts()),
)
async def edit_company_name_back_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await state.clear()

    if company_id:
        company_service = CompanyService(session)
        try:
            company = await company_service.get_company_detail(company_id)
        except CompanyNotFoundError:
            await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
            return

        await message.answer(
            _format_company_detail(user.language, company),
            reply_markup=build_company_detail_keyboard(company.id, page, user.language),
        )
        return

    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyEditStates.waiting_for_name)
async def edit_company_name_input_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    company_service = CompanyService(session)

    try:
        company = await company_service.update_company(
            company_id=company_id,
            payload=CompanyUpdateDTO(name=message.text or ""),
        )
    except CompanyNameValidationError:
        await message.answer(
            t(
                user.language,
                uz="Kompaniya nomi bo'sh bo'lmasin. Qayta kiriting.",
                ru="Название компании не должно быть пустым. Введите снова.",
                en="Company name cannot be empty. Please enter it again.",
            )
        )
        return
    except CompanyAlreadyExistsError:
        await message.answer(
            t(
                user.language,
                uz="Bunday kompaniya allaqachon mavjud. Boshqa nom kiriting.",
                ru="Такая компания уже существует. Введите другое название.",
                en="This company already exists. Please enter another name.",
            )
        )
        return
    except CompanyNotFoundError:
        await state.clear()
        await message.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            )
        )
        await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return

    await state.clear()
    await message.answer(
        t(
            user.language,
            uz="Kompaniya muvaffaqiyatli yangilandi.",
            ru="Компания успешно обновлена.",
            en="Company updated successfully.",
        )
    )
    await message.answer(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )
    await _restore_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(
    CompanyAdminAssignStates.waiting_for_telegram_id,
    LocalizedTextFilter(*company_menu_back_button_texts()),
)
async def assign_company_admin_back_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    await state.clear()

    if company_id:
        company_service = CompanyService(session)
        try:
            company = await company_service.get_company_detail(company_id)
        except CompanyNotFoundError:
            await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
            return

        await message.answer(
            _format_company_detail(user.language, company),
            reply_markup=build_company_detail_keyboard(company.id, page, user.language),
        )
        return

    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(CompanyAdminAssignStates.waiting_for_telegram_id)
async def assign_company_admin_input_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    raw_telegram_id = (message.text or "").strip()
    if not raw_telegram_id.isdigit():
        await message.answer(
            t(
                user.language,
                uz="Telegram ID faqat raqam bo'lishi kerak. Qayta kiriting.",
                ru="Telegram ID должен состоять только из цифр. Введите снова.",
                en="Telegram ID must contain only digits. Please enter it again.",
            )
        )
        return

    data = await state.get_data()
    company_id = int(data.get("company_id", 0))
    page = int(data.get("page", 1))
    company_admin_service = CompanyAdminService(session)

    try:
        company = await company_admin_service.assign_company_admin(
            CompanyAdminAssignDTO(
                company_id=company_id,
                telegram_id=int(raw_telegram_id),
            )
        )
    except InvalidTelegramIdError:
        await message.answer(
            t(
                user.language,
                uz="Telegram ID noto'g'ri. Qayta kiriting.",
                ru="Некорректный Telegram ID. Введите снова.",
                en="Invalid Telegram ID. Please enter it again.",
            )
        )
        return
    except CompanyNotFoundError:
        await state.clear()
        await message.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            )
        )
        await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)
        return

    await state.clear()
    await message.answer(
        t(
            user.language,
            uz="Company admin muvaffaqiyatli biriktirildi.",
            ru="Company admin успешно назначен.",
            en="Company admin assigned successfully.",
        )
    )
    await message.answer(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )
    await _restore_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(StateFilter(None), LocalizedTextFilter(*companies_button_texts()))
async def companies_menu_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await _show_company_menu(message, user.language or DEFAULT_LANGUAGE)


@router.message(StateFilter(None), LocalizedTextFilter(*add_company_button_texts()))
async def create_company_entry_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await state.clear()
    await state.set_state(CompanyCreateStates.waiting_for_name)
    await message.answer(
        t(
            user.language,
            uz="Yangi kompaniya nomini yuboring.",
            ru="Отправьте название новой компании.",
            en="Send the new company name.",
        ),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.message(StateFilter(None), LocalizedTextFilter(*company_list_button_texts()))
async def company_list_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await _answer_company_list_message(message, session, user.language, page=1)


@router.message(StateFilter(None), LocalizedTextFilter(*company_menu_back_button_texts()))
async def company_menu_back_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await state.clear()
    await _show_super_admin_panel(message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "company:noop")
async def company_noop_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(CompanyCreateStates.waiting_for_plan, F.data == "company:create:back")
async def create_company_plan_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return

    await state.set_state(CompanyCreateStates.waiting_for_name)
    await callback.answer()
    await callback.message.edit_text(
        t(
            user.language,
            uz="Kompaniya nomini yuboring.",
            ru="Отправьте название компании.",
            en="Send the company name.",
        )
    )


@router.callback_query(CompanyCreateStates.waiting_for_plan, F.data.startswith("company:create:plan:"))
async def create_company_plan_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    raw_plan = callback.data.rsplit(":", 1)[-1]

    try:
        plan = CompanyPlan(raw_plan)
    except ValueError:
        await callback.answer(
            t(
                user.language,
                uz="Noto'g'ri tarif tanlandi.",
                ru="Выбран некорректный тариф.",
                en="An invalid plan was selected.",
            ),
            show_alert=True,
        )
        return

    data = await state.get_data()
    company_name = str(data.get("company_name", "")).strip()
    company_service = CompanyService(session)

    try:
        company = await company_service.create_company(
            payload=CompanyCreateDTO(name=company_name, plan=plan)
        )
    except CompanyNameValidationError:
        await state.set_state(CompanyCreateStates.waiting_for_name)
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya nomi bo'sh bo'lmasin.",
                ru="Название компании не должно быть пустым.",
                en="Company name cannot be empty.",
            ),
            show_alert=True,
        )
        await callback.message.edit_text(
            t(
                user.language,
                uz="Kompaniya nomini yuboring.",
                ru="Отправьте название компании.",
                en="Send the company name.",
            )
        )
        return
    except CompanyAlreadyExistsError:
        await state.set_state(CompanyCreateStates.waiting_for_name)
        await callback.answer(
            t(
                user.language,
                uz="Bu nomdagi kompaniya allaqachon mavjud.",
                ru="Компания с таким названием уже существует.",
                en="A company with this name already exists.",
            ),
            show_alert=True,
        )
        await callback.message.edit_text(
            t(
                user.language,
                uz="Boshqa kompaniya nomini yuboring.",
                ru="Отправьте другое название компании.",
                en="Send another company name.",
            )
        )
        return

    await state.clear()
    await callback.answer(
        t(
            user.language,
            uz="Kompaniya yaratildi.",
            ru="Компания создана.",
            en="Company created.",
        )
    )
    await callback.message.edit_text(
        t(
            user.language,
            uz="Kompaniya muvaffaqiyatli yaratildi.",
            ru="Компания успешно создана.",
            en="The company has been created successfully.",
        )
    )
    await callback.message.answer(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, 1, user.language),
    )
    await _restore_company_menu(callback.message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "company:menu")
async def company_menu_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None:
        return

    await callback.answer()
    await callback.message.edit_text(
        t(
            user.language,
            uz="Kompaniyalar menyusiga qayting va kerakli bo'limni tanlang.",
            ru="Вернитесь в меню компаний и выберите нужный раздел.",
            en="Return to the companies menu and choose the required section.",
        )
    )
    await _show_company_menu(callback.message, user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data.startswith("company:list:"))
async def company_list_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()
    await _edit_company_list_message(callback.message, session, user.language, page=page)


@router.callback_query(F.data.startswith("company:detail:"))
async def company_detail_callback_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await callback.answer()
    await callback.message.edit_text(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )


@router.callback_query(F.data.startswith("company:toggle:"))
async def toggle_company_status_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.toggle_company_status(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await callback.answer(
        t(
            user.language,
            uz="Kompaniya holati yangilandi.",
            ru="Статус компании обновлен.",
            en="Company status updated.",
        )
    )
    await callback.message.edit_text(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )


@router.callback_query(F.data.startswith("company:assign:"))
async def assign_company_admin_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(company_id=company_id, page=page)
    await state.set_state(CompanyAdminAssignStates.waiting_for_telegram_id)
    await callback.answer()
    await callback.message.answer(
        t(
            user.language,
            uz="Company admin uchun Telegram ID yuboring.",
            ru="Отправьте Telegram ID для company admin.",
            en="Send the Telegram ID for the company admin.",
        ),
        reply_markup=build_company_flow_back_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("company:edit_menu:"))
async def edit_company_menu_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    await state.clear()
    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                _format_company_detail(user.language, company),
                "",
                t(
                    user.language,
                    uz="Tahrirlash uchun amalni tanlang.",
                    ru="Выберите действие для редактирования.",
                    en="Choose an edit action.",
                ),
            ]
        ),
        reply_markup=build_company_edit_keyboard(company.id, page, user.language),
    )


@router.callback_query(F.data.startswith("company:edit_name:"))
async def edit_company_name_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(company_id=company_id, page=page)
    await state.set_state(CompanyEditStates.waiting_for_name)
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


@router.callback_query(F.data.startswith("company:edit_plan_menu:"))
async def edit_company_plan_menu_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(company_id=company_id, page=page)
    await state.set_state(CompanyEditStates.waiting_for_plan)
    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                _format_company_detail(user.language, company),
                "",
                t(
                    user.language,
                    uz="Yangi tarifni tanlang.",
                    ru="Выберите новый тариф.",
                    en="Choose a new plan.",
                ),
            ]
        ),
        reply_markup=build_company_edit_plan_keyboard(company_id, page, user.language),
    )


@router.message(CompanyEditStates.waiting_for_plan)
async def edit_company_waiting_for_plan_message_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_message(message, session, settings)
    if user is None:
        return

    await message.answer(
        t(
            user.language,
            uz="Iltimos, tarifni inline tugmalar orqali tanlang.",
            ru="Пожалуйста, выберите тариф через inline-кнопки.",
            en="Please choose the plan using the inline buttons.",
        )
    )


@router.callback_query(CompanyEditStates.waiting_for_plan, F.data.startswith("company:edit_plan_select:"))
async def edit_company_plan_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw, plan_raw = callback.data.split(":", 4)
    company_id = int(company_id_raw)
    page = int(page_raw)

    try:
        plan = CompanyPlan(plan_raw)
    except ValueError:
        await callback.answer(
            t(
                user.language,
                uz="Noto'g'ri tarif tanlandi.",
                ru="Выбран некорректный тариф.",
                en="An invalid plan was selected.",
            ),
            show_alert=True,
        )
        return

    company_service = CompanyService(session)

    try:
        company = await company_service.update_company(
            company_id=company_id,
            payload=CompanyUpdateDTO(plan=plan),
        )
    except CompanyNotFoundError:
        await state.clear()
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer(
        t(
            user.language,
            uz="Tarif yangilandi.",
            ru="Тариф обновлен.",
            en="Plan updated.",
        )
    )
    await callback.message.edit_text(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )


@router.callback_query(F.data.startswith("company:delete:"))
async def delete_company_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(company_id=company_id, page=page)
    await state.set_state(CompanyDeleteStates.waiting_for_confirmation)
    await callback.answer()
    await callback.message.edit_text(
        "\n".join(
            [
                _format_company_detail(user.language, company),
                "",
                t(
                    user.language,
                    uz="Rostdan ham bu kompaniyani o'chirmoqchimisiz?",
                    ru="Вы действительно хотите удалить эту компанию?",
                    en="Do you really want to delete this company?",
                ),
            ]
        ),
        reply_markup=build_company_delete_confirmation_keyboard(company_id, page, user.language),
    )


@router.callback_query(CompanyDeleteStates.waiting_for_confirmation, F.data.startswith("company:delete_confirm:"))
async def delete_company_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        await company_service.delete_company(company_id)
    except CompanyNotFoundError:
        await state.clear()
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer(
        t(
            user.language,
            uz="Kompaniya o'chirildi.",
            ru="Компания удалена.",
            en="Company deleted.",
        )
    )
    await _edit_company_list_message(callback.message, session, user.language, page=page)


@router.callback_query(CompanyDeleteStates.waiting_for_confirmation, F.data.startswith("company:delete_cancel:"))
async def delete_company_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    user = await _require_super_admin_callback(callback, session, settings)
    if user is None or callback.message is None or callback.data is None:
        return

    _, _, company_id_raw, page_raw = callback.data.split(":", 3)
    company_id = int(company_id_raw)
    page = int(page_raw)
    company_service = CompanyService(session)

    try:
        company = await company_service.get_company_detail(company_id)
    except CompanyNotFoundError:
        await state.clear()
        await callback.answer(
            t(
                user.language,
                uz="Kompaniya topilmadi.",
                ru="Компания не найдена.",
                en="Company not found.",
            ),
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        _format_company_detail(user.language, company),
        reply_markup=build_company_detail_keyboard(company.id, page, user.language),
    )
