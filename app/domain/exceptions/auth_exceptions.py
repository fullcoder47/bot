from __future__ import annotations

from app.domain.enums.language import LanguageCode


class AuthError(Exception):
    """Base authentication exception."""


class LanguageSelectionRequiredError(AuthError):
    def __init__(self, language: LanguageCode | None = None) -> None:
        self.language = language
        super().__init__("Language selection is required.")


class AccessDeniedError(AuthError):
    def __init__(self, language: LanguageCode | None = None) -> None:
        self.language = language
        super().__init__("Access denied.")
