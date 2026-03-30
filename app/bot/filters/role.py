from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repo import UserRepository
from app.domain.dto.user_dto import UserDTO
from app.domain.enums.role import UserRole


class RoleFilter(BaseFilter):
    def __init__(self, *roles: UserRole) -> None:
        self.roles = set(roles)

    async def __call__(
        self,
        current_user: UserDTO | None = None,
        session: AsyncSession | None = None,
        event_from_user: Any | None = None,
    ) -> bool:
        resolved_user = current_user

        if resolved_user is None and session is not None and event_from_user is not None:
            user_repository = UserRepository(session)
            user = await user_repository.get_by_telegram_id(event_from_user.id)
            if user is not None:
                resolved_user = UserDTO.from_model(user)

        if resolved_user is None or not resolved_user.is_active:
            return False

        return resolved_user.role in self.roles
