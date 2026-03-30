from __future__ import annotations

import unicodedata

from aiogram.filters import BaseFilter
from aiogram.types import Message


def _extract_text(value: str | Message | None) -> str:
    if value is None:
        return ""

    if isinstance(value, Message):
        return value.text or value.caption or ""

    if isinstance(value, str):
        return value

    return ""


def normalize_button_text(text: str | Message | None) -> str:
    raw_text = _extract_text(text)
    if not raw_text:
        return ""

    normalized = unicodedata.normalize("NFKC", raw_text)
    normalized = normalized.replace("\ufe0f", "")
    return " ".join(normalized.split()).strip()


class LocalizedTextFilter(BaseFilter):
    def __init__(self, *texts: str) -> None:
        self.texts = {normalize_button_text(text) for text in texts}

    async def __call__(
        self,
        message: Message | None = None,
        text: str | None = None,
    ) -> bool:
        candidate = message if message is not None else text
        return normalize_button_text(candidate) in self.texts
