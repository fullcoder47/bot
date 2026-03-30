from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.company_dto import CompanyDTO
from app.domain.enums.company_plan import CompanyPlan
from app.domain.enums.language import LanguageCode


def build_company_plan_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="FREE", callback_data="company:create:plan:FREE")],
            [InlineKeyboardButton(text="BASIC", callback_data="company:create:plan:BASIC")],
            [InlineKeyboardButton(text="PRO", callback_data="company:create:plan:PRO")],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data="company:create:back",
                )
            ],
        ]
    )


def build_company_list_keyboard(
    companies: list[CompanyDTO],
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for company in companies:
        status_text = t(
            language,
            uz="Faol" if company.is_active else "Nofaol",
            ru="Активна" if company.is_active else "Неактивна",
            en="Active" if company.is_active else "Inactive",
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{company.name} ({company.plan.value} | {status_text})",
                    callback_data=f"company:detail:{company.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data="company:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_company_detail_keyboard(
    company_id: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="👤 Admin biriktirish", ru="👤 Назначить админа", en="👤 Assign admin"),
                    callback_data=f"company:assign:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🔁 Holatini almashtirish", ru="🔁 Сменить статус", en="🔁 Toggle status"),
                    callback_data=f"company:toggle:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data="company:list",
                )
            ],
        ]
    )
