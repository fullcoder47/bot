from __future__ import annotations

import unicodedata

from aiogram.filters import BaseFilter


def normalize_button_text(text: str | None) -> str:
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\ufe0f", "")
    return " ".join(normalized.split()).strip()


class LocalizedTextFilter(BaseFilter):
    def __init__(self, *texts: str) -> None:
        self.texts = {normalize_button_text(text) for text in texts}

    async def __call__(self, text: str | None = None) -> bool:
        return normalize_button_text(text) in self.texts
