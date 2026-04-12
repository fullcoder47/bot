from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.public_onboarding_dto import CompanyAdminApplicationDTO
from app.domain.enums.company_admin_application_status import CompanyAdminApplicationStatus
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode


def build_public_onboarding_home_keyboard(
    language: LanguageCode | str | None,
    application: CompanyAdminApplicationDTO | None,
    *,
    payment_card_available: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    status = application.status if application is not None else None
    can_start = status in {
        None,
        CompanyAdminApplicationStatus.DRAFT,
        CompanyAdminApplicationStatus.PAYMENT_REJECTED,
        CompanyAdminApplicationStatus.EXPIRED,
    }
    can_edit_company = status in {
        CompanyAdminApplicationStatus.PAYMENT_APPROVED,
        CompanyAdminApplicationStatus.APPLICATION_REJECTED,
    }
    can_submit = (
        can_edit_company
        and application is not None
        and bool(application.company_name)
        and application.company_plan is not None
    )

    if can_start:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="🚀 Ariza boshlash", ru="🚀 Начать заявку", en="🚀 Start application"),
                    callback_data="public:onboarding:start",
                )
            ]
        )

    if payment_card_available and can_start:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="💳 To'lovni boshlash", ru="💳 Начать оплату", en="💳 Start payment"),
                    callback_data="public:onboarding:pay",
                )
            ]
        )

    if can_edit_company:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="🏢 Kompaniya ma'lumotlari", ru="🏢 Данные компании", en="🏢 Company details"),
                    callback_data="public:onboarding:company",
                )
            ]
        )

    if can_submit:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Yuborish", ru="✅ Отправить", en="✅ Submit"),
                    callback_data="public:onboarding:submit",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="🔄 Yangilash", ru="🔄 Обновить", en="🔄 Refresh"),
                callback_data="public:onboarding:refresh",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_public_company_plan_keyboard(
    language: LanguageCode | str | None,
    current_plan: CompanyPlan | None = None,
) -> InlineKeyboardMarkup:
    def _label(plan: CompanyPlan) -> str:
        prefix = "• " if current_plan is plan else ""
        return f"{prefix}{plan.value}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_label(CompanyPlan.FREE), callback_data="public:onboarding:plan:FREE")],
            [InlineKeyboardButton(text=_label(CompanyPlan.BASIC), callback_data="public:onboarding:plan:BASIC")],
            [InlineKeyboardButton(text=_label(CompanyPlan.PRO), callback_data="public:onboarding:plan:PRO")],
        ]
    )


def build_public_payment_review_keyboard(
    application_id: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ To'lovni tasdiqlash", ru="✅ Подтвердить оплату", en="✅ Approve payment"),
                    callback_data=f"public:admin:payment:approve:{application_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="❌ To'lovni rad etish", ru="❌ Отклонить оплату", en="❌ Reject payment"),
                    callback_data=f"public:admin:payment:reject:{application_id}",
                )
            ],
        ]
    )


def build_public_final_review_keyboard(
    application_id: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Arizani tasdiqlash", ru="✅ Подтвердить заявку", en="✅ Approve application"),
                    callback_data=f"public:admin:application:approve:{application_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="❌ Arizani rad etish", ru="❌ Отклонить заявку", en="❌ Reject application"),
                    callback_data=f"public:admin:application:reject:{application_id}",
                )
            ],
        ]
    )
