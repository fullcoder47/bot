from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.company_dto import CompanyListPageDTO
from app.domain.enums.language import LanguageCode


def build_company_create_plan_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
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
    company_page: CompanyListPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for company in company_page.items:
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
                    callback_data=f"company:detail:{company.id}:{company_page.page}",
                )
            ]
        )

    navigation_row: list[InlineKeyboardButton] = []
    if company_page.page > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"company:list:{company_page.page - 1}",
            )
        )

    if company_page.total_pages > 1:
        navigation_row.append(
            InlineKeyboardButton(
                text=f"{company_page.page}/{company_page.total_pages}",
                callback_data="company:noop",
            )
        )

    if company_page.page < company_page.total_pages:
        navigation_row.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"company:list:{company_page.page + 1}",
            )
        )

    if navigation_row:
        rows.append(navigation_row)

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
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="👤 Admin biriktirish", ru="👤 Назначить админа", en="👤 Assign admin"),
                    callback_data=f"company:assign:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🔁 Holatini almashtirish", ru="🔁 Сменить статус", en="🔁 Toggle status"),
                    callback_data=f"company:toggle:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"company:edit_menu:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗑 O'chirish", ru="🗑 Удалить", en="🗑 Delete"),
                    callback_data=f"company:delete:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"company:list:{page}",
                )
            ],
        ]
    )


def build_company_edit_keyboard(
    company_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Nomini o'zgartirish", ru="✏️ Изменить название", en="✏️ Rename"),
                    callback_data=f"company:edit_name:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="📦 Tarifni o'zgartirish", ru="📦 Изменить тариф", en="📦 Change plan"),
                    callback_data=f"company:edit_plan_menu:{company_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"company:detail:{company_id}:{page}",
                )
            ],
        ]
    )


def build_company_edit_plan_keyboard(
    company_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="FREE", callback_data=f"company:edit_plan_select:{company_id}:{page}:FREE")],
            [InlineKeyboardButton(text="BASIC", callback_data=f"company:edit_plan_select:{company_id}:{page}:BASIC")],
            [InlineKeyboardButton(text="PRO", callback_data=f"company:edit_plan_select:{company_id}:{page}:PRO")],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"company:edit_menu:{company_id}:{page}",
                )
            ],
        ]
    )


def build_company_delete_confirmation_keyboard(
    company_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Ha", ru="✅ Да", en="✅ Yes"),
                    callback_data=f"company:delete_confirm:{company_id}:{page}",
                ),
                InlineKeyboardButton(
                    text=t(language, uz="❌ Yo'q", ru="❌ Нет", en="❌ No"),
                    callback_data=f"company:delete_cancel:{company_id}:{page}",
                ),
            ]
        ]
    )
