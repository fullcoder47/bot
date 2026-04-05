from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.text import LocalizedTextFilter
from app.bot.handlers.employee_common import require_employee_message
from app.bot.keyboards.reply.employee import rules_button_texts
from app.core.config import Settings
from app.core.localization import t

router = Router(name="employee")


def _rules_text(language) -> str:
    return "\n".join(
        [
            t(language, uz="Attendance qoidalari", ru="Правила attendance", en="Attendance rules"),
            t(language, uz="1. Joylashuvni yoqib, filial yaqinidan attendance qiling.", ru="1. Включите геолокацию и отмечайтесь рядом с филиалом.", en="1. Keep location enabled and attend near your branch."),
            t(language, uz="2. Joylashuv tekshiruvdan o'tgach dumaloq video yuboring.", ru="2. После проверки локации отправьте video note.", en="2. After location verification, send a video note."),
            t(language, uz="3. Ochiq session 10 daqiqada tugaydi.", ru="3. Открытая сессия истекает через 10 минут.", en="3. An open session expires after 10 minutes."),
            t(language, uz="4. Noto'g'ri urinishlar tizimda qayd etiladi.", ru="4. Некорректные попытки фиксируются системой.", en="4. Invalid attempts are recorded by the system."),
        ]
    )


@router.message(StateFilter(None), LocalizedTextFilter(*rules_button_texts()))
async def employee_rules_handler(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    access = await require_employee_message(message, session, settings)
    if access is None:
        return
    await message.answer(_rules_text(access.user.language))
