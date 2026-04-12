from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.company_admin import show_branch_menu
from app.bot.handlers.company_admin_common import require_company_admin_callback, require_company_admin_message
from app.bot.keyboards.inline.branches import (
    build_branch_detail_keyboard,
    build_branch_list_keyboard,
    build_branch_strict_keyboard,
)
from app.bot.keyboards.inline.common import build_confirmation_keyboard, build_yes_no_keyboard
from app.bot.keyboards.reply.company_admin import (
    add_branch_button_texts,
    back_button_texts,
    build_branch_location_input_keyboard,
    branch_list_button_texts,
    build_company_admin_flow_back_keyboard,
)
from app.bot.states.branch_states import BranchCreateStates, BranchEditStates, BranchLocationStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.domain.dto.branch_dto import BranchCreateDTO, BranchDTO, BranchUpdateDTO
from app.domain.exceptions.company_admin_exceptions import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidRadiusError,
)
from app.services.branch_service import BranchService

router = Router(name="branches")
BRANCH_PAGE_SIZE = BranchService.DEFAULT_PAGE_SIZE


def _format_branch_detail(language, branch: BranchDTO) -> str:
    status = t(language, uz="Faol" if branch.is_active else "Nofaol", ru="Активен" if branch.is_active else "Неактивен", en="Active" if branch.is_active else "Inactive")
    strict = t(language, uz="Ha" if branch.is_location_strict else "Yo'q", ru="Да" if branch.is_location_strict else "Нет", en="Yes" if branch.is_location_strict else "No")
    return "\n".join(
        [
            t(language, uz=f"🏢 Filial: {branch.name}", ru=f"🏢 Филиал: {branch.name}", en=f"🏢 Branch: {branch.name}"),
            t(language, uz=f"📍 Manzil: {branch.address or '-'}", ru=f"📍 Адрес: {branch.address or '-'}", en=f"📍 Address: {branch.address or '-'}"),
            t(language, uz=f"🧭 Latitude: {branch.latitude if branch.latitude is not None else '-'}", ru=f"🧭 Latitude: {branch.latitude if branch.latitude is not None else '-'}", en=f"🧭 Latitude: {branch.latitude if branch.latitude is not None else '-'}"),
            t(language, uz=f"🧭 Longitude: {branch.longitude if branch.longitude is not None else '-'}", ru=f"🧭 Longitude: {branch.longitude if branch.longitude is not None else '-'}", en=f"🧭 Longitude: {branch.longitude if branch.longitude is not None else '-'}"),
            t(language, uz=f"📏 Radius: {branch.allowed_radius_meters if branch.allowed_radius_meters is not None else '-'}", ru=f"📏 Радиус: {branch.allowed_radius_meters if branch.allowed_radius_meters is not None else '-'}", en=f"📏 Radius: {branch.allowed_radius_meters if branch.allowed_radius_meters is not None else '-'}"),
            t(language, uz=f"📍 Strict: {strict}", ru=f"📍 Строгая локация: {strict}", en=f"📍 Strict location: {strict}"),
            t(language, uz=f"🔁 Holati: {status}", ru=f"🔁 Статус: {status}", en=f"🔁 Status: {status}"),
        ]
    )


def _format_branch_create_summary(language, data: dict[str, object]) -> str:
    strict = t(language, uz="Ha" if data.get("is_location_strict") else "Yo'q", ru="Да" if data.get("is_location_strict") else "Нет", en="Yes" if data.get("is_location_strict") else "No")
    return "\n".join(
        [
            t(language, uz="Yangi filialni tasdiqlang.", ru="Подтвердите новый филиал.", en="Confirm the new branch."),
            t(language, uz=f"🏢 Nomi: {data.get('name', '-')}", ru=f"🏢 Название: {data.get('name', '-')}", en=f"🏢 Name: {data.get('name', '-')}"),
            t(language, uz=f"📍 Manzil: {data.get('address') or '-'}", ru=f"📍 Адрес: {data.get('address') or '-'}", en=f"📍 Address: {data.get('address') or '-'}"),
            t(language, uz=f"🧭 Latitude: {data.get('latitude') if data.get('latitude') is not None else '-'}", ru=f"🧭 Latitude: {data.get('latitude') if data.get('latitude') is not None else '-'}", en=f"🧭 Latitude: {data.get('latitude') if data.get('latitude') is not None else '-'}"),
            t(language, uz=f"🧭 Longitude: {data.get('longitude') if data.get('longitude') is not None else '-'}", ru=f"🧭 Longitude: {data.get('longitude') if data.get('longitude') is not None else '-'}", en=f"🧭 Longitude: {data.get('longitude') if data.get('longitude') is not None else '-'}"),
            t(language, uz=f"📏 Radius: {data.get('allowed_radius_meters') if data.get('allowed_radius_meters') is not None else '-'}", ru=f"📏 Радиус: {data.get('allowed_radius_meters') if data.get('allowed_radius_meters') is not None else '-'}", en=f"📏 Radius: {data.get('allowed_radius_meters') if data.get('allowed_radius_meters') is not None else '-'}"),
            t(language, uz=f"📍 Strict: {strict}", ru=f"📍 Строгая локация: {strict}", en=f"📍 Strict location: {strict}"),
        ]
    )


async def _show_branch_list(message: Message, service: BranchService, company_id: int, language, page: int = 1) -> None:
    branch_page = await service.list_branches(company_id, page=page, page_size=BRANCH_PAGE_SIZE)
    await message.answer(
        t(language, uz=f"Filiallar ro'yxati ({branch_page.page}/{branch_page.total_pages})", ru=f"Список филиалов ({branch_page.page}/{branch_page.total_pages})", en=f"Branch list ({branch_page.page}/{branch_page.total_pages})"),
        reply_markup=build_branch_list_keyboard(branch_page, language),
    )


async def _handle_shared_location_input(
    message: Message,
    state: FSMContext,
    language,
    next_state,
) -> bool:
    if message.location is None:
        return False

    try:
        latitude, longitude = BranchService.parse_shared_location(
            message.location.latitude,
            message.location.longitude,
        )
    except (InvalidLatitudeError, InvalidLongitudeError):
        await message.answer(
            t(
                language,
                uz="Yuborilgan joylashuv noto'g'ri. Qayta yuboring.",
                ru="Отправленная локация некорректна. Отправьте снова.",
                en="The shared location is invalid. Please send it again.",
            )
        )
        return True

    await state.update_data(latitude=latitude, longitude=longitude)
    await state.set_state(next_state)
    await message.answer(
        t(
            language,
            uz="Joylashuv qabul qilindi. Endi radiusni yuboring yoki `-` yuboring.",
            ru="Локация принята. Теперь отправьте радиус или `-`.",
            en="Location received. Now send the radius or `-`.",
        ),
        reply_markup=build_company_admin_flow_back_keyboard(language),
    )
    return True


@router.message(LocalizedTextFilter(*add_branch_button_texts()))
async def add_branch_entry_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await state.set_state(BranchCreateStates.waiting_for_name)
    await message.answer(
        t(access.user.language, uz="Filial nomini yuboring.", ru="Отправьте название филиала.", en="Send the branch name."),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(LocalizedTextFilter(*branch_list_button_texts()))
async def branch_list_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await _show_branch_list(message, BranchService(session), access.company.id, access.user.language)


@router.message(
    BranchCreateStates.waiting_for_name,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_address,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_latitude,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_longitude,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_radius,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_strict,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchCreateStates.waiting_for_confirmation,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchEditStates.waiting_for_name,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchEditStates.waiting_for_address,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchEditStates.waiting_for_confirmation,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchLocationStates.waiting_for_latitude,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchLocationStates.waiting_for_longitude,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchLocationStates.waiting_for_radius,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchLocationStates.waiting_for_strict,
    LocalizedTextFilter(*back_button_texts()),
)
@router.message(
    BranchLocationStates.waiting_for_confirmation,
    LocalizedTextFilter(*back_button_texts()),
)
async def branch_flow_back_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.clear()
    await show_branch_menu(message, access.user.language or DEFAULT_LANGUAGE)


@router.message(BranchCreateStates.waiting_for_name)
async def branch_create_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    normalized_name = BranchService.normalize_name(message.text or "")
    if not normalized_name:
        await message.answer(t(access.user.language, uz="Filial nomi bo'sh bo'lmasin.", ru="Название филиала не должно быть пустым.", en="Branch name cannot be empty."))
        return
    await state.update_data(name=normalized_name)
    await state.set_state(BranchCreateStates.waiting_for_address)
    await message.answer(
        t(access.user.language, uz="Filial manzilini yuboring yoki `-` yuboring.", ru="Отправьте адрес филиала или `-`.", en="Send the branch address or send `-`."),
    )


@router.message(BranchCreateStates.waiting_for_address)
async def branch_create_address_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.update_data(address=BranchService.normalize_optional_text(message.text or ""))
    await state.set_state(BranchCreateStates.waiting_for_latitude)
    await message.answer(
        t(access.user.language, uz="Latitude yuboring, Telegram orqali joylashuv ulashing yoki `-` yuboring.", ru="Отправьте latitude, поделитесь геолокацией через Telegram или отправьте `-`.", en="Send latitude, share a Telegram location, or send `-`."),
        reply_markup=build_branch_location_input_keyboard(access.user.language),
    )


@router.message(BranchCreateStates.waiting_for_latitude)
async def branch_create_latitude_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    if await _handle_shared_location_input(
        message,
        state,
        access.user.language,
        BranchCreateStates.waiting_for_radius,
    ):
        return
    try:
        latitude = BranchService.parse_optional_latitude(message.text or "")
    except InvalidLatitudeError:
        await message.answer(t(access.user.language, uz="Latitude noto'g'ri. Qayta kiriting.", ru="Некорректный latitude. Введите снова.", en="Invalid latitude. Please enter it again."))
        return
    await state.update_data(latitude=latitude)
    await state.set_state(BranchCreateStates.waiting_for_longitude)
    await message.answer(
        t(access.user.language, uz="Longitude yuboring, joylashuv ulashing yoki `-` yuboring.", ru="Отправьте longitude, поделитесь локацией или отправьте `-`.", en="Send longitude, share a location, or send `-`."),
        reply_markup=build_branch_location_input_keyboard(access.user.language),
    )


@router.message(BranchCreateStates.waiting_for_longitude)
async def branch_create_longitude_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    if await _handle_shared_location_input(
        message,
        state,
        access.user.language,
        BranchCreateStates.waiting_for_radius,
    ):
        return
    data = await state.get_data()
    try:
        longitude = BranchService.parse_optional_longitude(message.text or "")
        BranchService.validate_location_fields(data.get("latitude"), longitude, None)
    except InvalidLongitudeError:
        await message.answer(t(access.user.language, uz="Longitude noto'g'ri. Qayta kiriting.", ru="Некорректный longitude. Введите снова.", en="Invalid longitude. Please enter it again."))
        return
    except InvalidLatitudeError:
        await message.answer(t(access.user.language, uz="Latitude va longitude ikkalasi birga kiritilishi kerak.", ru="Latitude и longitude должны быть заполнены вместе.", en="Latitude and longitude must be provided together."))
        return
    await state.update_data(longitude=longitude)
    await state.set_state(BranchCreateStates.waiting_for_radius)
    await message.answer(
        t(access.user.language, uz="Radiusni yuboring yoki `-` yuboring.", ru="Отправьте радиус или `-`.", en="Send the radius or `-`."),
    )


@router.message(BranchCreateStates.waiting_for_radius)
async def branch_create_radius_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    data = await state.get_data()
    try:
        radius = BranchService.parse_optional_radius(message.text or "")
        BranchService.validate_location_fields(data.get("latitude"), data.get("longitude"), radius)
    except InvalidRadiusError:
        await message.answer(t(access.user.language, uz="Radius noto'g'ri. Musbat son kiriting.", ru="Некорректный радиус. Введите положительное число.", en="Invalid radius. Enter a positive number."))
        return
    except (InvalidLatitudeError, InvalidLongitudeError):
        await message.answer(t(access.user.language, uz="Latitude va longitude ikkalasi birga kiritilishi kerak.", ru="Latitude и longitude должны быть заполнены вместе.", en="Latitude and longitude must be provided together."))
        return
    await state.update_data(allowed_radius_meters=radius)
    await state.set_state(BranchCreateStates.waiting_for_strict)
    await message.answer(
        t(access.user.language, uz="Lokatsiya strict bo'lsinmi?", ru="Сделать локацию строгой?", en="Should location be strict?"),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )
    await message.answer(
        t(access.user.language, uz="Tanlang:", ru="Выберите:", en="Choose:"),
        reply_markup=build_branch_strict_keyboard(access.user.language),
    )


@router.callback_query(BranchCreateStates.waiting_for_strict, F.data.startswith("branch:strict:"))
async def branch_create_strict_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    is_strict = callback.data.endswith("true")
    await state.update_data(is_location_strict=is_strict)
    await state.set_state(BranchCreateStates.waiting_for_confirmation)
    data = await state.get_data()
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_create_summary(access.user.language, data),
        reply_markup=build_confirmation_keyboard("branch:create:confirm", "branch:create:cancel", access.user.language),
    )


@router.message(BranchCreateStates.waiting_for_confirmation)
async def branch_create_waiting_confirmation_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, tasdiqlash uchun inline tugmalardan foydalaning.", ru="Пожалуйста, используйте inline-кнопки для подтверждения.", en="Please use the inline buttons to confirm."))


@router.callback_query(BranchCreateStates.waiting_for_confirmation, F.data == "branch:create:confirm")
async def branch_create_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    service = BranchService(session)
    try:
        branch = await service.create_branch(
            access.company.id,
            BranchCreateDTO(
                name=str(data.get("name", "")),
                address=data.get("address") if isinstance(data.get("address"), str) else None,
                latitude=data.get("latitude") if isinstance(data.get("latitude"), float) else None,
                longitude=data.get("longitude") if isinstance(data.get("longitude"), float) else None,
                allowed_radius_meters=data.get("allowed_radius_meters") if isinstance(data.get("allowed_radius_meters"), int) else None,
                is_location_strict=bool(data.get("is_location_strict", True)),
            ),
            actor_telegram_id=access.user.telegram_id,
        )
    except BranchAlreadyExistsError:
        await callback.answer(t(access.user.language, uz="Bunday filial allaqachon mavjud.", ru="Такой филиал уже существует.", en="This branch already exists."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Filial yaratildi.", ru="Филиал создан.", en="Branch created."))
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, 1, access.user.language),
    )


@router.callback_query(BranchCreateStates.waiting_for_confirmation, F.data == "branch:create:cancel")
async def branch_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(t(access.user.language, uz="Filial yaratish bekor qilindi.", ru="Создание филиала отменено.", en="Branch creation cancelled."))
    await show_branch_menu(callback.message, access.user.language or DEFAULT_LANGUAGE)


@router.callback_query(F.data == "branch:noop")
async def branch_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("branch:list:"))
async def branch_list_callback_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    page = int(callback.data.rsplit(":", 1)[-1])
    branch_page = await BranchService(session).list_branches(access.company.id, page=page, page_size=BRANCH_PAGE_SIZE)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz=f"Filiallar ro'yxati ({branch_page.page}/{branch_page.total_pages})", ru=f"Список филиалов ({branch_page.page}/{branch_page.total_pages})", en=f"Branch list ({branch_page.page}/{branch_page.total_pages})"),
        reply_markup=build_branch_list_keyboard(branch_page, access.user.language),
    )


@router.callback_query(F.data.startswith("branch:detail:"))
async def branch_detail_callback_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    try:
        branch = await BranchService(session).get_branch(access.company.id, int(branch_id_raw))
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.regexp(r"^branch:edit:\d+:\d+$"))
async def branch_edit_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    try:
        branch = await BranchService(session).get_branch(access.company.id, int(branch_id_raw))
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await state.clear()
    await state.update_data(
        branch_id=int(branch_id_raw),
        page=int(page_raw),
        latitude=branch.latitude,
        longitude=branch.longitude,
        allowed_radius_meters=branch.allowed_radius_meters,
        is_location_strict=branch.is_location_strict,
        is_active=branch.is_active,
    )
    await state.set_state(BranchEditStates.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        t(access.user.language, uz=f"Yangi filial nomini yuboring.\nJoriy nom: {branch.name}", ru=f"Отправьте новое название филиала.\nТекущее название: {branch.name}", en=f"Send the new branch name.\nCurrent name: {branch.name}"),
        reply_markup=build_company_admin_flow_back_keyboard(access.user.language),
    )


@router.message(BranchEditStates.waiting_for_name)
async def branch_edit_name_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    normalized_name = BranchService.normalize_name(message.text or "")
    if not normalized_name:
        await message.answer(t(access.user.language, uz="Filial nomi bo'sh bo'lmasin.", ru="Название филиала не должно быть пустым.", en="Branch name cannot be empty."))
        return
    await state.update_data(name=normalized_name)
    await state.set_state(BranchEditStates.waiting_for_address)
    await message.answer(
        t(access.user.language, uz="Yangi manzilni yuboring yoki `-` yuboring.", ru="Отправьте новый адрес или `-`.", en="Send the new address or `-`."),
    )


@router.message(BranchEditStates.waiting_for_address)
async def branch_edit_address_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await state.update_data(address=BranchService.normalize_optional_text(message.text or ""))
    data = await state.get_data()
    await state.set_state(BranchEditStates.waiting_for_confirmation)
    await message.answer(
        _format_branch_create_summary(
            access.user.language,
            {
                "name": data.get("name"),
                "address": data.get("address"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "allowed_radius_meters": data.get("allowed_radius_meters"),
                "is_location_strict": data.get("is_location_strict", True),
            },
        ),
        reply_markup=build_confirmation_keyboard("branch:edit:confirm", "branch:edit:cancel", access.user.language),
    )


@router.message(BranchEditStates.waiting_for_confirmation)
@router.message(BranchLocationStates.waiting_for_confirmation)
async def branch_waiting_confirmation_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    await message.answer(t(access.user.language, uz="Iltimos, tasdiqlash uchun inline tugmalardan foydalaning.", ru="Пожалуйста, используйте inline-кнопки для подтверждения.", en="Please use the inline buttons to confirm."))


@router.callback_query(BranchEditStates.waiting_for_confirmation, F.data == "branch:edit:confirm")
async def branch_edit_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    branch_id = int(data.get("branch_id", 0))
    page = int(data.get("page", 1))
    current = await BranchService(session).get_branch(access.company.id, branch_id)
    try:
        branch = await BranchService(session).update_branch(
            access.company.id,
            branch_id,
            BranchUpdateDTO(
                name=str(data.get("name", "")),
                address=data.get("address") if isinstance(data.get("address"), str) else None,
                latitude=current.latitude,
                longitude=current.longitude,
                allowed_radius_meters=current.allowed_radius_meters,
                is_location_strict=current.is_location_strict,
                is_active=current.is_active,
            ),
            actor_telegram_id=access.user.telegram_id,
        )
    except (BranchAlreadyExistsError, BranchNotFoundError):
        await callback.answer(t(access.user.language, uz="Filialni yangilab bo'lmadi.", ru="Не удалось обновить филиал.", en="Could not update the branch."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Filial yangilandi.", ru="Филиал обновлён.", en="Branch updated."))
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, page, access.user.language),
    )


@router.callback_query(BranchEditStates.waiting_for_confirmation, F.data == "branch:edit:cancel")
async def branch_edit_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    branch_id = int(data.get("branch_id", 0))
    page = int(data.get("page", 1))
    await state.clear()
    branch = await BranchService(session).get_branch(access.company.id, branch_id)
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, page, access.user.language),
    )


@router.callback_query(F.data.regexp(r"^branch:location:\d+:\d+$"))
async def branch_location_entry_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    try:
        branch = await BranchService(session).get_branch(access.company.id, int(branch_id_raw))
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await state.clear()
    await state.update_data(branch_id=int(branch_id_raw), page=int(page_raw), name=branch.name, address=branch.address, is_active=branch.is_active)
    await state.set_state(BranchLocationStates.waiting_for_latitude)
    await callback.answer()
    await callback.message.answer(
        t(access.user.language, uz="Yangi latitude yuboring, joylashuv ulashing yoki `-` yuboring.", ru="Отправьте новый latitude, поделитесь локацией или отправьте `-`.", en="Send the new latitude, share a location, or send `-`."),
        reply_markup=build_branch_location_input_keyboard(access.user.language),
    )


@router.message(BranchLocationStates.waiting_for_latitude)
async def branch_location_latitude_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    if await _handle_shared_location_input(
        message,
        state,
        access.user.language,
        BranchLocationStates.waiting_for_radius,
    ):
        return
    try:
        latitude = BranchService.parse_optional_latitude(message.text or "")
    except InvalidLatitudeError:
        await message.answer(t(access.user.language, uz="Latitude noto'g'ri.", ru="Некорректный latitude.", en="Invalid latitude."))
        return
    await state.update_data(latitude=latitude)
    await state.set_state(BranchLocationStates.waiting_for_longitude)
    await message.answer(
        t(access.user.language, uz="Yangi longitude yuboring, joylashuv ulashing yoki `-` yuboring.", ru="Отправьте новый longitude, поделитесь локацией или отправьте `-`.", en="Send the new longitude, share a location, or send `-`."),
        reply_markup=build_branch_location_input_keyboard(access.user.language),
    )


@router.message(BranchLocationStates.waiting_for_longitude)
async def branch_location_longitude_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    if await _handle_shared_location_input(
        message,
        state,
        access.user.language,
        BranchLocationStates.waiting_for_radius,
    ):
        return
    data = await state.get_data()
    try:
        longitude = BranchService.parse_optional_longitude(message.text or "")
        BranchService.validate_location_fields(data.get("latitude"), longitude, None)
    except (InvalidLongitudeError, InvalidLatitudeError):
        await message.answer(t(access.user.language, uz="Latitude va longitude mos emas.", ru="Latitude и longitude указаны некорректно.", en="Latitude and longitude do not match correctly."))
        return
    await state.update_data(longitude=longitude)
    await state.set_state(BranchLocationStates.waiting_for_radius)
    await message.answer(t(access.user.language, uz="Yangi radiusni yuboring yoki `-` yuboring.", ru="Отправьте новый радиус или `-`.", en="Send the new radius or `-`.")) 


@router.message(BranchLocationStates.waiting_for_radius)
async def branch_location_radius_handler(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_message(message, session, settings)
    if access is None:
        return
    data = await state.get_data()
    try:
        radius = BranchService.parse_optional_radius(message.text or "")
        BranchService.validate_location_fields(data.get("latitude"), data.get("longitude"), radius)
    except (InvalidRadiusError, InvalidLatitudeError, InvalidLongitudeError):
        await message.answer(t(access.user.language, uz="Lokatsiya yoki radius noto'g'ri.", ru="Некорректная локация или радиус.", en="Invalid location or radius."))
        return
    await state.update_data(allowed_radius_meters=radius)
    await state.set_state(BranchLocationStates.waiting_for_strict)
    await message.answer(
        t(access.user.language, uz="Lokatsiya strict bo'lsinmi?", ru="Сделать локацию строгой?", en="Should location be strict?"),
        reply_markup=build_branch_strict_keyboard(access.user.language),
    )


@router.callback_query(BranchLocationStates.waiting_for_strict, F.data.startswith("branch:strict:"))
async def branch_location_strict_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    await state.update_data(is_location_strict=callback.data.endswith("true"))
    await state.set_state(BranchLocationStates.waiting_for_confirmation)
    data = await state.get_data()
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_create_summary(access.user.language, data),
        reply_markup=build_confirmation_keyboard("branch:location:confirm", "branch:location:cancel", access.user.language),
    )


@router.callback_query(BranchLocationStates.waiting_for_confirmation, F.data == "branch:location:confirm")
async def branch_location_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    branch_id = int(data.get("branch_id", 0))
    page = int(data.get("page", 1))
    try:
        branch = await BranchService(session).update_branch(
            access.company.id,
            branch_id,
            BranchUpdateDTO(
                name=str(data.get("name", "")),
                address=data.get("address") if isinstance(data.get("address"), str) else None,
                latitude=data.get("latitude") if isinstance(data.get("latitude"), float) else None,
                longitude=data.get("longitude") if isinstance(data.get("longitude"), float) else None,
                allowed_radius_meters=data.get("allowed_radius_meters") if isinstance(data.get("allowed_radius_meters"), int) else None,
                is_location_strict=bool(data.get("is_location_strict", True)),
                is_active=bool(data.get("is_active", True)),
            ),
            actor_telegram_id=access.user.telegram_id,
        )
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await state.clear()
    await callback.answer(t(access.user.language, uz="Lokatsiya yangilandi.", ru="Локация обновлена.", en="Location updated."))
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, page, access.user.language),
    )


@router.callback_query(BranchLocationStates.waiting_for_confirmation, F.data == "branch:location:cancel")
async def branch_location_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None:
        return
    data = await state.get_data()
    branch_id = int(data.get("branch_id", 0))
    page = int(data.get("page", 1))
    await state.clear()
    branch = await BranchService(session).get_branch(access.company.id, branch_id)
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, page, access.user.language),
    )


@router.callback_query(F.data.startswith("branch:toggle:"))
async def branch_toggle_callback_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    try:
        branch = await BranchService(session).toggle_branch_status(access.company.id, int(branch_id_raw), actor_telegram_id=access.user.telegram_id)
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, int(page_raw), access.user.language),
    )


@router.callback_query(F.data.startswith("branch:delete:"))
async def branch_delete_entry_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    await callback.answer()
    await callback.message.edit_text(
        t(access.user.language, uz="Rostdan ham filialni o'chirmoqchimisiz?", ru="Вы действительно хотите удалить филиал?", en="Do you really want to delete this branch?"),
        reply_markup=build_yes_no_keyboard(
            f"branch:delete_confirm:{branch_id_raw}:{page_raw}",
            f"branch:delete_cancel:{branch_id_raw}:{page_raw}",
            access.user.language,
        ),
    )


@router.callback_query(F.data.startswith("branch:delete_confirm:"))
async def branch_delete_confirm_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    service = BranchService(session)
    try:
        detached_count = await service.delete_branch(
            access.company.id,
            int(branch_id_raw),
            actor_telegram_id=access.user.telegram_id,
        )
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    branch_page = await service.list_branches(access.company.id, page=int(page_raw), page_size=BRANCH_PAGE_SIZE)
    await callback.answer(t(access.user.language, uz="Filial o'chirildi.", ru="Филиал удалён.", en="Branch deleted."))
    await callback.message.edit_text(
        "\n".join(
            [
                t(access.user.language, uz=f"Filiallar ro'yxati ({branch_page.page}/{branch_page.total_pages})", ru=f"Список филиалов ({branch_page.page}/{branch_page.total_pages})", en=f"Branch list ({branch_page.page}/{branch_page.total_pages})"),
                t(access.user.language, uz="Filial o'chirildi.", ru="Филиал удалён.", en="Branch deleted."),
                t(
                    access.user.language,
                    uz=f"{detached_count} ta ishchidan filial biriktiruvi olib tashlandi." if detached_count else "Biriktirilgan ishchi topilmadi.",
                    ru=f"У {detached_count} сотрудников филиал был отвязан." if detached_count else "Привязанных сотрудников не было.",
                    en=f"Branch assignment was removed from {detached_count} employees." if detached_count else "There were no linked employees.",
                ),
            ]
        ),
        reply_markup=build_branch_list_keyboard(branch_page, access.user.language),
    )


@router.callback_query(F.data.startswith("branch:delete_cancel:"))
async def branch_delete_cancel_handler(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    access = await require_company_admin_callback(callback, session, settings)
    if access is None or callback.message is None or callback.data is None:
        return
    _, _, branch_id_raw, page_raw = callback.data.split(":", 3)
    try:
        branch = await BranchService(session).get_branch(access.company.id, int(branch_id_raw))
    except BranchNotFoundError:
        await callback.answer(t(access.user.language, uz="Filial topilmadi.", ru="Филиал не найден.", en="Branch not found."), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        _format_branch_detail(access.user.language, branch),
        reply_markup=build_branch_detail_keyboard(branch, int(page_raw), access.user.language),
    )
