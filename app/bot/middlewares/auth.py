from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware

from app.core.config import Settings
from app.core.localization import DEFAULT_LANGUAGE
from app.db.repositories.user_repo import UserRepository
from app.domain.dto.user_dto import UserDTO


class AuthContextMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["settings"] = self.settings
        data["current_user"] = None
        data["lang"] = DEFAULT_LANGUAGE

        event_from_user = data.get("event_from_user")
        session = data.get("session")

        if event_from_user is not None and session is not None:
            user_repository = UserRepository(session)
            user = await user_repository.get_by_telegram_id(event_from_user.id)
            if user is not None:
                current_user = UserDTO.from_model(user)
                data["current_user"] = current_user
                data["lang"] = current_user.language or DEFAULT_LANGUAGE

        return await handler(event, data)
