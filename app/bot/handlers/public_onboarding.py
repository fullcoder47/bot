from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline.public_onboarding import (
    build_public_company_plan_keyboard,
    build_public_final_review_keyboard,
    build_public_onboarding_home_keyboard,
    build_public_payment_review_keyboard,
)
from app.bot.states.public_onboarding_states import PublicOnboardingStates
from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE, t
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.public_onboarding_dto import CompanyAdminApplicationDTO
from app.domain.dto.user_dto import TelegramUserDTO
from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode
from app.domain.exceptions.auth_exceptions import AccessDeniedError, LanguageSelectionRequiredError
from app.domain.exceptions.company_admin_exceptions import InvalidPhoneError
from app.domain.exceptions.company_exceptions import CompanyAlreadyExistsError, CompanyNameValidationError
from app.domain.exceptions.public_onboarding_exceptions import (
    ApplicationNotFoundError,
    InvalidApplicationStateError,
    PaymentCardNotConfiguredError,
    PaymentWindowExpiredError,
)
from app.services.auth_service import AuthService
from app.services.public_onboarding_service import PublicOnboardingService
from app.services.system_settings_service import SystemSettingsService

router = Router(name="public_onboarding")
logger = logging.getLogger(__name__)


def _status_label(language, status: CompanyAdminApplicationStatus | None) -> str:
    mapping = {
        None: t(language, uz="Boshlanmagan", ru="Не начато", en="Not started"),
        CompanyAdminApplicationStatus.DRAFT: t(language, uz="Ariza tayyorlanmoqda", ru="Заявка готовится", en="Draft"),
        CompanyAdminApplicationStatus.AWAITING_PAYMENT: t(language, uz="To'lov cheki kutilmoqda", ru="Ожидается чек оплаты", en="Awaiting payment receipt"),
        CompanyAdminApplicationStatus.PAYMENT_SUBMITTED: t(language, uz="To'lov tekshirilmoqda", ru="Оплата проверяется", en="Payment under review"),
        CompanyAdminApplicationStatus.PAYMENT_APPROVED: t(language, uz="To'lov tasdiqlangan", ru="Оплата подтверждена", en="Payment approved"),
        CompanyAdminApplicationStatus.PENDING_FINAL_APPROVAL: t(language, uz="Yakuniy tasdiq kutilmoqda", ru="Ожидается финальное подтверждение", en="Awaiting final approval"),
        CompanyAdminApplicationStatus.APPROVED: t(language, uz="Tasdiqlangan", ru="Подтверждено", en="Approved"),
        CompanyAdminApplicationStatus.PAYMENT_REJECTED: t(language, uz="To'lov rad etilgan", ru="Оплата отклонена", en="Payment rejected"),
        CompanyAdminApplicationStatus.APPLICATION_REJECTED: t(language, uz="Ariza qayta ishlash uchun qaytarilgan", ru="Заявка возвращена на доработку", en="Application returned for revision"),
        CompanyAdminApplicationStatus.EXPIRED: t(language, uz="To'lov vaqti tugagan", ru="Время оплаты истекло", en="Payment window expired"),
    }
    return mapping[status]


def _format_dt(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def _application_summary(language, application: CompanyAdminApplicationDTO | None) -> list[str]:
    if application is None:
        return [t(language, uz="Status: Boshlanmagan", ru="Статус: Не начато", en="Status: Not started")]

    lines = [
        t(language, uz=f"Status: {_status_label(language, application.status)}", ru=f"Статус: {_status_label(language, application.status)}", en=f"Status: {_status_label(language, application.status)}"),
    ]
    if application.payment_deadline_at is not None and application.status is CompanyAdminApplicationStatus.AWAITING_PAYMENT:
        lines.append(
            t(
                language,
                uz=f"To'lov cheki muddati: {_format_dt(application.payment_deadline_at)}",
                ru=f"Дедлайн чека оплаты: {_format_dt(application.payment_deadline_at)}",
                en=f"Payment receipt deadline: {_format_dt(application.payment_deadline_at)}",
            )
        )
    if application.company_name:
        lines.append(t(language, uz=f"Kompaniya: {application.company_name}", ru=f"Компания: {application.company_name}", en=f"Company: {application.company_name}"))
    if application.company_plan is not None:
        lines.append(t(language, uz=f"Tarif: {application.company_plan.value}", ru=f"Тариф: {application.company_plan.value}", en=f"Plan: {application.company_plan.value}"))
    if application.contact_phone:
        lines.append(t(language, uz=f"Kontakt: {application.contact_phone}", ru=f"Контакт: {application.contact_phone}", en=f"Contact: {application.contact_phone}"))
    if application.rejection_reason:
        lines.append(t(language, uz=f"Izoh: {application.rejection_reason}", ru=f"Комментарий: {application.rejection_reason}", en=f"Comment: {application.rejection_reason}"))
    return lines


def _public_home_text(
    language,
    application: CompanyAdminApplicationDTO | None,
    *,
    payment_card_available: bool,
) -> str:
    card_line = t(
        language,
        uz="To'lov qismi hozircha faol." if payment_card_available else "To'lov qismi hozircha sozlanmagan.",
        ru="Платежный этап сейчас активен." if payment_card_available else "Платежный этап пока не настроен.",
        en="The payment step is active." if payment_card_available else "The payment step is not configured yet.",
    )
    return "\n".join(
        [
            t(language, uz="Attendance bot nimalarni qila oladi?", ru="Что умеет attendance bot?", en="What can this attendance bot do?"),
            t(language, uz="• kompaniya ichki tuzilmasini boshqarish", ru="• управлять внутренней структурой компании", en="• manage the company structure"),
            t(language, uz="• xodimlar va smenalarni yuritish", ru="• вести сотрудников и смены", en="• manage employees and shifts"),
            t(language, uz="• davomat, lokatsiya va video note orqali nazorat", ru="• контролировать attendance по локации и video note", en="• control attendance with location and video note"),
            t(language, uz="• real vaqt bildirishnomalari", ru="• уведомления в реальном времени", en="• real-time notifications"),
            "",
            card_line,
            *_application_summary(language, application),
            "",
            t(
                language,
                uz="Agar bot sizga mos bo'lsa, ariza qoldirib to'lovni yuboring. To'lov tasdiqlangach kompaniyangizni yaratib, company admin sifatida ishni boshlaysiz.",
                ru="Если бот вам подходит, оставьте заявку и отправьте оплату. После подтверждения оплаты вы создадите свою компанию и начнете работу как company admin.",
                en="If the bot fits your needs, submit an application and payment. After payment approval, you will create your company and start as a company admin.",
            ),
        ]
    )


def _company_draft_text(language, application: CompanyAdminApplicationDTO) -> str:
    return "\n".join(
        [
            t(language, uz="Company admin arizasi", ru="Заявка company admin", en="Company admin application"),
            t(language, uz=f"Kompaniya nomi: {application.company_name or '-'}", ru=f"Название компании: {application.company_name or '-'}", en=f"Company name: {application.company_name or '-'}"),
            t(language, uz=f"Tarif: {application.company_plan.value if application.company_plan else '-'}", ru=f"Тариф: {application.company_plan.value if application.company_plan else '-'}", en=f"Plan: {application.company_plan.value if application.company_plan else '-'}"),
            t(language, uz=f"Kontakt telefon: {application.contact_phone or '-'}", ru=f"Контактный телефон: {application.contact_phone or '-'}", en=f"Contact phone: {application.contact_phone or '-'}"),
        ]
    )


def _payment_review_text(language, application: CompanyAdminApplicationDTO) -> str:
    return "\n".join(
        [
            t(language, uz="Yangi to'lov cheki", ru="Новый платежный чек", en="New payment receipt"),
            t(language, uz=f"Ariza ID: {application.id}", ru=f"ID заявки: {application.id}", en=f"Application ID: {application.id}"),
            t(language, uz=f"F.I.Sh: {application.full_name}", ru=f"Ф.И.О.: {application.full_name}", en=f"Full name: {application.full_name}"),
            t(language, uz=f"Telegram ID: {application.telegram_id}", ru=f"Telegram ID: {application.telegram_id}", en=f"Telegram ID: {application.telegram_id}"),
            t(language, uz=f"Username: @{application.username}" if application.username else "Username: -", ru=f"Username: @{application.username}" if application.username else "Username: -", en=f"Username: @{application.username}" if application.username else "Username: -"),
            t(language, uz=f"Yuborilgan vaqt: {_format_dt(application.payment_submitted_at)}", ru=f"Время отправки: {_format_dt(application.payment_submitted_at)}", en=f"Submitted at: {_format_dt(application.payment_submitted_at)}"),
        ]
    )


def _final_review_text(language, application: CompanyAdminApplicationDTO) -> str:
    return "\n".join(
        [
            t(language, uz="Yangi company admin arizasi", ru="Новая заявка company admin", en="New company admin application"),
            t(language, uz=f"Ariza ID: {application.id}", ru=f"ID заявки: {application.id}", en=f"Application ID: {application.id}"),
            t(language, uz=f"F.I.Sh: {application.full_name}", ru=f"Ф.И.О.: {application.full_name}", en=f"Full name: {application.full_name}"),
            t(language, uz=f"Telegram ID: {application.telegram_id}", ru=f"Telegram ID: {application.telegram_id}", en=f"Telegram ID: {application.telegram_id}"),
            t(language, uz=f"Kompaniya: {application.company_name or '-'}", ru=f"Компания: {application.company_name or '-'}", en=f"Company: {application.company_name or '-'}"),
            t(language, uz=f"Tarif: {application.company_plan.value if application.company_plan else '-'}", ru=f"Тариф: {application.company_plan.value if application.company_plan else '-'}", en=f"Plan: {application.company_plan.value if application.company_plan else '-'}"),
            t(language, uz=f"Kontakt: {application.contact_phone or '-'}", ru=f"Контакт: {application.contact_phone or '-'}", en=f"Contact: {application.contact_phone or '-'}"),
            t(language, uz=f"To'lov tasdiqlangan: {_format_dt(application.payment_approved_at)}", ru=f"Оплата подтверждена: {_format_dt(application.payment_approved_at)}", en=f"Payment approved: {_format_dt(application.payment_approved_at)}"),
        ]
    )


async def _build_public_home_payload(
    session: AsyncSession,
    telegram_user: TelegramUserDTO,
    language: LanguageCode,
) -> tuple[str, object]:
    onboarding_service = PublicOnboardingService(session)
    application = await onboarding_service.get_application_by_telegram_id(telegram_user.telegram_id)
    payment_card_available = await SystemSettingsService(session).get_payment_card_number() is not None
    text = _public_home_text(language, application, payment_card_available=payment_card_available)
    keyboard = build_public_onboarding_home_keyboard(language, application, payment_card_available=payment_card_available)
    return text, keyboard


async def show_public_onboarding_home(
    message: Message,
    session: AsyncSession,
    telegram_user: TelegramUserDTO,
    language: LanguageCode,
) -> None:
    text, keyboard = await _build_public_home_payload(session, telegram_user, language)
    await message.answer(text, reply_markup=keyboard)


async def edit_public_onboarding_home(
    message: Message,
    session: AsyncSession,
    telegram_user: TelegramUserDTO,
    language: LanguageCode,
) -> None:
    text, keyboard = await _build_public_home_payload(session, telegram_user, language)
    await message.edit_text(text, reply_markup=keyboard)


async def _require_super_admin_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
):
    auth_service = AuthService(session, settings)
    try:
        return await auth_service.require_super_admin(callback.from_user.id)
    except LanguageSelectionRequiredError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Avval /start buyrug'ini yuboring.", ru="Сначала отправьте команду /start.", en="Please send /start first."),
            show_alert=True,
        )
    except AccessDeniedError as exc:
        await callback.answer(
            t(exc.language or DEFAULT_LANGUAGE, uz="Sizda bu amal uchun huquq yo'q.", ru="У вас нет прав для этого действия.", en="You do not have permission for this action."),
            show_alert=True,
        )
    return None


async def _edit_callback_message(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    if callback.message is None:
        return
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
        return
    await callback.message.edit_text(text, reply_markup=reply_markup)


async def _resolve_public_language(
    session: AsyncSession,
    telegram_id: int,
) -> LanguageCode:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if user is not None and user.language is not None:
        return user.language
    return DEFAULT_LANGUAGE


async def _notify_super_admins_about_payment(
    event: CallbackQuery | Message,
    settings: Settings,
    application: CompanyAdminApplicationDTO,
) -> None:
    if application.payment_receipt_file_id is None:
        return

    caption = _payment_review_text(DEFAULT_LANGUAGE, application)
    keyboard = build_public_payment_review_keyboard(application.id, DEFAULT_LANGUAGE)
    for super_admin_id in settings.super_admin_id_set:
        try:
            await event.bot.send_photo(
                super_admin_id,
                photo=application.payment_receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception(
                "Failed to send payment review message to super admin telegram_id=%s application_id=%s",
                super_admin_id,
                application.id,
            )


async def _notify_super_admins_about_final_application(
    event: CallbackQuery | Message,
    settings: Settings,
    application: CompanyAdminApplicationDTO,
) -> None:
    text = _final_review_text(DEFAULT_LANGUAGE, application)
    keyboard = build_public_final_review_keyboard(application.id, DEFAULT_LANGUAGE)
    for super_admin_id in settings.super_admin_id_set:
        try:
            await event.bot.send_message(
                super_admin_id,
                text,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception(
                "Failed to send final review message to super admin telegram_id=%s application_id=%s",
                super_admin_id,
                application.id,
            )


@router.callback_query(F.data == "public:onboarding:refresh")
async def public_onboarding_refresh_handler(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return
    telegram_user = TelegramUserDTO.from_aiogram(callback.from_user)
    onboarding_service = PublicOnboardingService(session)
    application = await onboarding_service.get_application_by_telegram_id(telegram_user.telegram_id)
    language = application.language if application is not None else await _resolve_public_language(session, telegram_user.telegram_id)
    await callback.answer()
    await edit_public_onboarding_home(callback.message, session, telegram_user, language)


@router.callback_query(F.data == "public:onboarding:start")
async def public_onboarding_start_handler(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return
    telegram_user = TelegramUserDTO.from_aiogram(callback.from_user)
    language = await _resolve_public_language(session, telegram_user.telegram_id)
    application = await PublicOnboardingService(session).start_application(telegram_user, language)
    await callback.answer(
        t(application.language, uz="Ariza jarayoni tayyor.", ru="Процесс заявки подготовлен.", en="The application flow is ready."),
    )
    await edit_public_onboarding_home(callback.message, session, telegram_user, application.language)


@router.callback_query(F.data == "public:onboarding:pay")
async def public_onboarding_pay_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return

    telegram_user = TelegramUserDTO.from_aiogram(callback.from_user)
    onboarding_service = PublicOnboardingService(session)
    language = await _resolve_public_language(session, telegram_user.telegram_id)
    try:
        application, payment_card = await onboarding_service.start_payment(telegram_user, language)
    except PaymentCardNotConfiguredError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Hozircha to'lov kartasi sozlanmagan.", ru="Платежная карта пока не настроена.", en="The payment card is not configured yet."),
            show_alert=True,
        )
        return
    except InvalidApplicationStateError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Bu bosqich uchun to'lovni qayta boshlab bo'lmaydi.", ru="Для этого этапа нельзя повторно запустить оплату.", en="Payment cannot be restarted at this stage."),
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(PublicOnboardingStates.waiting_for_receipt_photo)
    await callback.answer()
    await callback.message.answer(
        "\n".join(
            [
                t(application.language, uz="To'lovni quyidagi kartaga yuboring:", ru="Отправьте оплату на следующую карту:", en="Send the payment to the following card:"),
                payment_card,
                t(application.language, uz=f"Chekni 20 daqiqa ichida yuboring. Deadline: {_format_dt(application.payment_deadline_at)}", ru=f"Отправьте чек в течение 20 минут. Дедлайн: {_format_dt(application.payment_deadline_at)}", en=f"Send the receipt within 20 minutes. Deadline: {_format_dt(application.payment_deadline_at)}"),
                t(application.language, uz="Keyin to'lov cheki rasmini shu chatga yuboring.", ru="После этого отправьте фотографию чека в этот чат.", en="Then send the receipt photo to this chat."),
            ]
        )
    )


@router.message(PublicOnboardingStates.waiting_for_receipt_photo, F.photo)
async def public_onboarding_receipt_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if message.from_user is None or not message.photo:
        return

    largest_photo = message.photo[-1]
    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.submit_payment_receipt(
            message.from_user.id,
            file_id=largest_photo.file_id,
            file_unique_id=largest_photo.file_unique_id,
        )
    except ApplicationNotFoundError:
        await state.clear()
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Ariza topilmadi. /start dan qayta boshlang.", ru="Заявка не найдена. Начните заново через /start.", en="Application not found. Restart from /start."),
        )
        return
    except PaymentWindowExpiredError:
        await state.clear()
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="To'lov cheki yuborish muddati tugagan. Jarayonni qayta boshlang.", ru="Срок отправки чека истек. Запустите процесс заново.", en="The payment receipt deadline has expired. Please start again."),
        )
        return
    except InvalidApplicationStateError:
        await state.clear()
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Hozir bu bosqich faol emas.", ru="Сейчас этот этап не активен.", en="This step is not active right now."),
        )
        return

    await state.clear()
    await message.answer(
        t(application.language, uz="Chek qabul qilindi va super admin tasdig'iga yuborildi.", ru="Чек принят и отправлен супер администратору на подтверждение.", en="The receipt was received and sent to the super admin for approval."),
    )
    await _notify_super_admins_about_payment(message, settings, application)
    telegram_user = TelegramUserDTO.from_aiogram(message.from_user)
    await show_public_onboarding_home(message, session, telegram_user, application.language)


@router.message(PublicOnboardingStates.waiting_for_receipt_photo)
async def public_onboarding_receipt_invalid_handler(message: Message) -> None:
    await message.answer(
        t(DEFAULT_LANGUAGE, uz="Iltimos, to'lov cheki rasmini yuboring.", ru="Пожалуйста, отправьте фотографию чека.", en="Please send a photo of the payment receipt."),
    )


@router.callback_query(F.data == "public:onboarding:company")
async def public_onboarding_company_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return

    onboarding_service = PublicOnboardingService(session)
    application = await onboarding_service.get_application_by_telegram_id(callback.from_user.id)
    if application is None or application.status not in {
        CompanyAdminApplicationStatus.PAYMENT_APPROVED,
        CompanyAdminApplicationStatus.APPLICATION_REJECTED,
    }:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Avval to'lov tasdiqlanishi kerak.", ru="Сначала оплата должна быть подтверждена.", en="The payment must be approved first."),
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(PublicOnboardingStates.waiting_for_company_name)
    await callback.answer()
    await callback.message.answer(
        t(
            application.language,
            uz=f"Kompaniya nomini yuboring. Joriy nom: {application.company_name or '-'}",
            ru=f"Отправьте название компании. Текущее название: {application.company_name or '-'}",
            en=f"Send the company name. Current name: {application.company_name or '-'}",
        )
    )


@router.message(PublicOnboardingStates.waiting_for_company_name)
async def public_onboarding_company_name_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.save_company_name(message.from_user.id, message.text or "")
    except CompanyNameValidationError:
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Kompaniya nomi bo'sh bo'lmasin.", ru="Название компании не должно быть пустым.", en="Company name cannot be empty."),
        )
        return
    except CompanyAlreadyExistsError:
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Bunday kompaniya allaqachon mavjud. Boshqa nom kiriting.", ru="Такая компания уже существует. Укажите другое название.", en="This company already exists. Please choose another name."),
        )
        return
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await state.clear()
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Bu bosqich hozir faol emas. /start orqali qayta oching.", ru="Сейчас этот этап не активен. Откройте его снова через /start.", en="This step is not active right now. Open it again via /start."),
        )
        return

    await state.set_state(PublicOnboardingStates.waiting_for_company_plan)
    await message.answer(
        _company_draft_text(application.language, application),
        reply_markup=build_public_company_plan_keyboard(application.language, application.company_plan),
    )


@router.message(PublicOnboardingStates.waiting_for_company_plan)
async def public_onboarding_company_plan_invalid_message_handler(message: Message) -> None:
    await message.answer(
        t(DEFAULT_LANGUAGE, uz="Iltimos, tarifni inline tugmalar orqali tanlang.", ru="Пожалуйста, выберите тариф через inline-кнопки.", en="Please choose the plan using the inline buttons."),
    )


@router.callback_query(PublicOnboardingStates.waiting_for_company_plan, F.data.startswith("public:onboarding:plan:"))
async def public_onboarding_company_plan_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None or callback.data is None:
        return

    try:
        plan = CompanyPlan(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Noto'g'ri tarif tanlandi.", ru="Выбран некорректный тариф.", en="An invalid plan was selected."),
            show_alert=True,
        )
        return

    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.save_company_plan(callback.from_user.id, plan)
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await state.clear()
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Bu bosqich hozir faol emas.", ru="Сейчас этот этап не активен.", en="This step is not active right now."),
            show_alert=True,
        )
        return

    await state.set_state(PublicOnboardingStates.waiting_for_contact_phone)
    await callback.answer()
    await callback.message.edit_text(_company_draft_text(application.language, application))
    await callback.message.answer(
        t(
            application.language,
            uz=f"Kontakt telefonni yuboring. O'tkazib yuborish uchun `-` yuboring. Joriy: {application.contact_phone or '-'}",
            ru=f"Отправьте контактный телефон. Чтобы пропустить, отправьте `-`. Текущий: {application.contact_phone or '-'}",
            en=f"Send the contact phone. Send `-` to skip. Current: {application.contact_phone or '-'}",
        )
    )


@router.message(PublicOnboardingStates.waiting_for_contact_phone)
async def public_onboarding_contact_phone_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    onboarding_service = PublicOnboardingService(session)
    try:
        phone = onboarding_service.parse_optional_phone(message.text or "")
        application = await onboarding_service.save_contact_phone(message.from_user.id, phone)
    except InvalidPhoneError:
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Telefon raqami noto'g'ri. Masalan: +998901234567 yoki `-` yuboring.", ru="Некорректный номер телефона. Например: +998901234567 или отправьте `-`.", en="Invalid phone number. Example: +998901234567 or send `-`."),
        )
        return
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await state.clear()
        await message.answer(
            t(DEFAULT_LANGUAGE, uz="Bu bosqich hozir faol emas.", ru="Сейчас этот этап не активен.", en="This step is not active right now."),
        )
        return

    await state.clear()
    await message.answer(
        _company_draft_text(application.language, application),
        reply_markup=build_public_onboarding_home_keyboard(
            application.language,
            application,
            payment_card_available=True,
        ),
    )


@router.callback_query(F.data == "public:onboarding:submit")
async def public_onboarding_submit_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.submit_final_application(callback.from_user.id)
    except InvalidApplicationStateError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Ariza yuborish uchun ma'lumotlarni to'ldiring.", ru="Заполните данные перед отправкой заявки.", en="Fill in the data before submitting the application."),
            show_alert=True,
        )
        return
    except CompanyAlreadyExistsError:
        await callback.answer(
            t(DEFAULT_LANGUAGE, uz="Bu kompaniya nomi band bo'lib qoldi. Iltimos, boshqasini tanlang.", ru="Это название компании уже занято. Выберите другое.", en="This company name is no longer available. Please choose another one."),
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer(
        t(application.language, uz="Ariza super admin tasdig'iga yuborildi.", ru="Заявка отправлена супер админу на подтверждение.", en="The application was sent to the super admin for approval."),
    )
    await _notify_super_admins_about_final_application(callback, settings, application)
    if callback.message is not None:
        telegram_user = TelegramUserDTO.from_aiogram(callback.from_user)
        await edit_public_onboarding_home(callback.message, session, telegram_user, application.language)


@router.callback_query(F.data.startswith("public:admin:payment:approve:"))
async def public_admin_payment_approve_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    admin_user = await _require_super_admin_callback(callback, session, settings)
    if admin_user is None or callback.data is None:
        return

    application_id = int(callback.data.rsplit(":", 1)[-1])
    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.approve_payment(
            application_id,
            actor_telegram_id=admin_user.telegram_id,
        )
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await callback.answer(
            t(admin_user.language, uz="Bu to'lov arizasi endi tasdiqlanmaydi.", ru="Эта платежная заявка больше недоступна для подтверждения.", en="This payment request can no longer be approved."),
            show_alert=True,
        )
        return

    await callback.answer(t(admin_user.language, uz="To'lov tasdiqlandi.", ru="Оплата подтверждена.", en="Payment approved."))
    await _edit_callback_message(
        callback,
        _payment_review_text(admin_user.language, application) + "\n\n" + t(admin_user.language, uz="Natija: Tasdiqlandi", ru="Результат: Подтверждено", en="Result: Approved"),
        reply_markup=None,
    )
    try:
        await callback.bot.send_message(
            application.telegram_id,
            t(
                application.language,
                uz="To'lovingiz tasdiqlandi. Endi kompaniya ma'lumotlarini to'ldiring.",
                ru="Ваш платеж подтвержден. Теперь заполните данные компании.",
                en="Your payment was approved. Now fill in the company details.",
            ),
        )
    except Exception:
        logger.exception("Failed to notify applicant about payment approval application_id=%s", application.id)


@router.callback_query(F.data.startswith("public:admin:payment:reject:"))
async def public_admin_payment_reject_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    admin_user = await _require_super_admin_callback(callback, session, settings)
    if admin_user is None or callback.data is None:
        return

    application_id = int(callback.data.rsplit(":", 1)[-1])
    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.reject_payment(
            application_id,
            actor_telegram_id=admin_user.telegram_id,
        )
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await callback.answer(
            t(admin_user.language, uz="Bu to'lov arizasi endi rad etilmaydi.", ru="Эта платежная заявка больше недоступна для отклонения.", en="This payment request can no longer be rejected."),
            show_alert=True,
        )
        return

    await callback.answer(t(admin_user.language, uz="To'lov rad etildi.", ru="Оплата отклонена.", en="Payment rejected."))
    await _edit_callback_message(
        callback,
        _payment_review_text(admin_user.language, application) + "\n\n" + t(admin_user.language, uz="Natija: Rad etildi", ru="Результат: Отклонено", en="Result: Rejected"),
        reply_markup=None,
    )
    try:
        await callback.bot.send_message(
            application.telegram_id,
            t(
                application.language,
                uz="To'lovingiz rad etildi. Kerak bo'lsa /start orqali qayta urinib ko'ring.",
                ru="Ваш платеж отклонен. При необходимости попробуйте снова через /start.",
                en="Your payment was rejected. If needed, try again via /start.",
            ),
        )
    except Exception:
        logger.exception("Failed to notify applicant about payment rejection application_id=%s", application.id)


@router.callback_query(F.data.startswith("public:admin:application:approve:"))
async def public_admin_application_approve_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    admin_user = await _require_super_admin_callback(callback, session, settings)
    if admin_user is None or callback.data is None:
        return

    application_id = int(callback.data.rsplit(":", 1)[-1])
    onboarding_service = PublicOnboardingService(session)
    try:
        application, company = await onboarding_service.approve_final_application(
            application_id,
            actor_telegram_id=admin_user.telegram_id,
        )
    except (ApplicationNotFoundError, InvalidApplicationStateError, CompanyAlreadyExistsError):
        await callback.answer(
            t(admin_user.language, uz="Arizani tasdiqlab bo'lmadi.", ru="Не удалось подтвердить заявку.", en="Could not approve the application."),
            show_alert=True,
        )
        return

    await callback.answer(
        t(admin_user.language, uz="Ariza tasdiqlandi.", ru="Заявка подтверждена.", en="Application approved.")
    )
    await _edit_callback_message(
        callback,
        _final_review_text(admin_user.language, application) + "\n\n" + t(admin_user.language, uz=f"Natija: Tasdiqlandi. Kompaniya yaratildi: {company.name}", ru=f"Результат: Подтверждено. Компания создана: {company.name}", en=f"Result: Approved. Company created: {company.name}"),
        reply_markup=None,
    )
    try:
        await callback.bot.send_message(
            application.telegram_id,
            t(
                application.language,
                uz=f"Arizangiz tasdiqlandi. {company.name} kompaniyasi yaratildi. Endi /start bosib company admin panelga kiring.",
                ru=f"Ваша заявка подтверждена. Компания {company.name} создана. Теперь нажмите /start и войдите в панель company admin.",
                en=f"Your application was approved. The company {company.name} was created. Now press /start to enter the company admin panel.",
            ),
        )
    except Exception:
        logger.exception("Failed to notify applicant about final approval application_id=%s", application.id)


@router.callback_query(F.data.startswith("public:admin:application:reject:"))
async def public_admin_application_reject_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    admin_user = await _require_super_admin_callback(callback, session, settings)
    if admin_user is None or callback.data is None:
        return

    application_id = int(callback.data.rsplit(":", 1)[-1])
    onboarding_service = PublicOnboardingService(session)
    try:
        application = await onboarding_service.reject_final_application(
            application_id,
            actor_telegram_id=admin_user.telegram_id,
        )
    except (ApplicationNotFoundError, InvalidApplicationStateError):
        await callback.answer(
            t(admin_user.language, uz="Bu arizani endi rad etib bo'lmaydi.", ru="Эту заявку больше нельзя отклонить.", en="This application can no longer be rejected."),
            show_alert=True,
        )
        return

    await callback.answer(
        t(admin_user.language, uz="Ariza tahrir uchun qaytarildi.", ru="Заявка возвращена на доработку.", en="The application was returned for revision.")
    )
    await _edit_callback_message(
        callback,
        _final_review_text(admin_user.language, application) + "\n\n" + t(admin_user.language, uz="Natija: Tahrir uchun qaytarildi", ru="Результат: Возвращено на доработку", en="Result: Returned for revision"),
        reply_markup=None,
    )
    try:
        await callback.bot.send_message(
            application.telegram_id,
            t(
                application.language,
                uz="Arizangiz tahrir uchun qaytarildi. /start orqali ma'lumotlarni yangilab qayta yuboring.",
                ru="Ваша заявка возвращена на доработку. Обновите данные через /start и отправьте снова.",
                en="Your application was returned for revision. Update the details via /start and submit again.",
            ),
        )
    except Exception:
        logger.exception("Failed to notify applicant about final rejection application_id=%s", application.id)
