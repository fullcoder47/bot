from __future__ import annotations

from typing import TypeAlias

from app.domain.enums.language import LanguageCode

LanguageLike: TypeAlias = LanguageCode | str | None
DEFAULT_LANGUAGE = LanguageCode.UZ


def normalize_language(language: LanguageLike) -> LanguageCode:
    if isinstance(language, LanguageCode):
        return language

    if isinstance(language, str):
        normalized = language.strip().lower()
        for item in LanguageCode:
            if item.value == normalized:
                return item

    return DEFAULT_LANGUAGE


def t(language: LanguageLike, *, uz: str, ru: str, en: str) -> str:
    resolved_language = normalize_language(language)

    if resolved_language is LanguageCode.RU:
        return ru

    if resolved_language is LanguageCode.EN:
        return en

    return uz
