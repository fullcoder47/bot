from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.company_dto import CompanyDetailDTO, CompanyListFiltersDTO, CompanyListPageDTO
from app.domain.enums.language import LanguageCode


def _marked(selected: bool, text: str) -> str:
    return f"• {text}" if selected else text


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


def build_company_action_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Tasdiqlash", ru="✅ Подтвердить", en="✅ Confirm"),
                    callback_data=confirm_callback,
                ),
                InlineKeyboardButton(
                    text=t(language, uz="❌ Bekor qilish", ru="❌ Отмена", en="❌ Cancel"),
                    callback_data=cancel_callback,
                ),
            ]
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
    company: CompanyDetailDTO,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=t(
                    language,
                    uz="🔄 Adminni almashtirish" if company.has_admin_assignment else "👤 Admin biriktirish",
                    ru="🔄 Сменить админа" if company.has_admin_assignment else "👤 Назначить админа",
                    en="🔄 Replace admin" if company.has_admin_assignment else "👤 Assign admin",
                ),
                callback_data=f"company:assign_entry:{company.id}:{page}",
            )
        ]
    ]

    if company.has_admin_assignment and company.admin_assignment_is_active:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="⛔ Adminni deaktiv qilish", ru="⛔ Деактивировать админа", en="⛔ Deactivate admin"),
                    callback_data=f"company:admin_deactivate:{company.id}:{page}",
                )
            ]
        )

    if company.has_admin_assignment:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, uz="🧹 Adminni olib tashlash", ru="🧹 Убрать админа", en="🧹 Remove admin"),
                    callback_data=f"company:admin_remove:{company.id}:{page}",
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="✅ Aktiv qilish" if not company.is_active else "⛔ Deaktiv qilish",
                        ru="✅ Активировать" if not company.is_active else "⛔ Деактивировать",
                        en="✅ Activate" if not company.is_active else "⛔ Deactivate",
                    ),
                    callback_data=f"company:toggle:{company.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="💳 Tarifni almashtirish", ru="💳 Изменить тариф", en="💳 Change plan"),
                    callback_data=f"company:plan_menu:{company.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="📅 Subscription yangilash", ru="📅 Обновить подписку", en="📅 Update subscription"),
                    callback_data=f"company:subscription_entry:{company.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"company:edit:{company.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗑 O'chirish", ru="🗑 Удалить", en="🗑 Delete"),
                    callback_data=f"company:delete:{company.id}:{page}",
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

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_company_plan_update_keyboard(
    company_id: int,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="FREE", callback_data=f"company:plan_select:{company_id}:{page}:FREE")],
            [InlineKeyboardButton(text="BASIC", callback_data=f"company:plan_select:{company_id}:{page}:BASIC")],
            [InlineKeyboardButton(text="PRO", callback_data=f"company:plan_select:{company_id}:{page}:PRO")],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"company:detail:{company_id}:{page}",
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


def build_company_filter_keyboard(
    filters: CompanyListFiltersDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    status_all = t(language, uz="Barchasi", ru="Все", en="All")
    status_active = t(language, uz="Faol", ru="Активные", en="Active")
    status_inactive = t(language, uz="Nofaol", ru="Неактивные", en="Inactive")
    expired_label = t(language, uz="Muddati tugaganlar", ru="Истекшие", en="Expired only")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_marked(filters.is_active is None, status_all),
                    callback_data="company:filter:status:all",
                ),
                InlineKeyboardButton(
                    text=_marked(filters.is_active is True, status_active),
                    callback_data="company:filter:status:active",
                ),
                InlineKeyboardButton(
                    text=_marked(filters.is_active is False, status_inactive),
                    callback_data="company:filter:status:inactive",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_marked(filters.plan is None, t(language, uz="Tarif: barchasi", ru="Тариф: все", en="Plan: all")),
                    callback_data="company:filter:plan:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_marked(filters.plan is not None and filters.plan.value == "FREE", "FREE"),
                    callback_data="company:filter:plan:FREE",
                ),
                InlineKeyboardButton(
                    text=_marked(filters.plan is not None and filters.plan.value == "BASIC", "BASIC"),
                    callback_data="company:filter:plan:BASIC",
                ),
                InlineKeyboardButton(
                    text=_marked(filters.plan is not None and filters.plan.value == "PRO", "PRO"),
                    callback_data="company:filter:plan:PRO",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_marked(filters.expired_only, expired_label),
                    callback_data=f"company:filter:expired:{'off' if filters.expired_only else 'on'}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="✅ Qo'llash", ru="✅ Применить", en="✅ Apply"),
                    callback_data="company:filter:apply",
                ),
                InlineKeyboardButton(
                    text=t(language, uz="🧹 Tozalash", ru="🧹 Сбросить", en="🧹 Clear"),
                    callback_data="company:filter:clear",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data="company:filter:back",
                )
            ],
        ]
    )
