from __future__ import annotations

from aiogram.filters import BaseFilter

from app.domain.dto.user_dto import UserDTO
from app.domain.enums.role import UserRole


class RoleFilter(BaseFilter):
    def __init__(self, *roles: UserRole) -> None:
        self.roles = set(roles)

    async def __call__(self, current_user: UserDTO | None) -> bool:
        if current_user is None or not current_user.is_active:
            return False

        return current_user.role in self.roles
