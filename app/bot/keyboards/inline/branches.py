from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.localization import t
from app.domain.dto.branch_dto import BranchDTO, BranchListPageDTO
from app.domain.enums.language import LanguageCode


def build_branch_list_keyboard(
    branch_page: BranchListPageDTO,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for branch in branch_page.items:
        status = t(language, uz="Faol" if branch.is_active else "Nofaol", ru="Активен" if branch.is_active else "Неактивен", en="Active" if branch.is_active else "Inactive")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{branch.name} ({status})",
                    callback_data=f"branch:detail:{branch.id}:{branch_page.page}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if branch_page.page > 1:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Oldingi", ru="⬅️ Назад", en="⬅️ Prev"),
                callback_data=f"branch:list:{branch_page.page - 1}",
            )
        )
    if branch_page.total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{branch_page.page}/{branch_page.total_pages}", callback_data="branch:noop"))
    if branch_page.page < branch_page.total_pages:
        nav.append(
            InlineKeyboardButton(
                text=t(language, uz="Keyingi ➡️", ru="Далее ➡️", en="Next ➡️"),
                callback_data=f"branch:list:{branch_page.page + 1}",
            )
        )
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                callback_data="branch:menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_branch_detail_keyboard(
    branch: BranchDTO,
    page: int,
    language: LanguageCode | str | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, uz="✏️ Tahrirlash", ru="✏️ Редактировать", en="✏️ Edit"),
                    callback_data=f"branch:edit:{branch.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="📍 Lokatsiyani yangilash", ru="📍 Обновить локацию", en="📍 Update location"),
                    callback_data=f"branch:location:{branch.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(
                        language,
                        uz="⛔ Deaktiv qilish" if branch.is_active else "✅ Aktiv qilish",
                        ru="⛔ Деактивировать" if branch.is_active else "✅ Активировать",
                        en="⛔ Deactivate" if branch.is_active else "✅ Activate",
                    ),
                    callback_data=f"branch:toggle:{branch.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="🗑 O'chirish", ru="🗑 Удалить", en="🗑 Delete"),
                    callback_data=f"branch:delete:{branch.id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(language, uz="⬅️ Orqaga", ru="⬅️ Назад", en="⬅️ Back"),
                    callback_data=f"branch:list:{page}",
                )
            ],
        ]
    )


def build_branch_strict_keyboard(language: LanguageCode | str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(language, uz="✅ Ha", ru="✅ Да", en="✅ Yes"), callback_data="branch:strict:true"),
                InlineKeyboardButton(text=t(language, uz="❌ Yo'q", ru="❌ Нет", en="❌ No"), callback_data="branch:strict:false"),
            ]
        ]
    )
