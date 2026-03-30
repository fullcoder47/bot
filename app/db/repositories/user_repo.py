from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.domain.dto.user_dto import CreateUserDTO, TelegramUserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        statement = select(User).where(User.telegram_id == telegram_id)
        return await self.session.scalar(statement)

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None

    async def create(self, payload: CreateUserDTO) -> User:
        user = User(
            telegram_id=payload.telegram_id,
            full_name=payload.full_name,
            username=payload.username,
            phone=payload.phone,
            role=payload.role,
            language=payload.language,
            is_active=payload.is_active,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_language(self, user: User, language: LanguageCode) -> User:
        user.language = language
        await self.session.flush()
        return user

    async def update_profile_fields(self, user: User, payload: TelegramUserDTO) -> User:
        user.full_name = payload.full_name
        user.username = payload.username
        user.phone = payload.phone
        await self.session.flush()
        return user

    async def update_role_and_status(
        self,
        user: User,
        role: UserRole,
        is_active: bool,
    ) -> User:
        user.role = role
        user.is_active = is_active
        await self.session.flush()
        return user

    async def promote_to_super_admin_if_allowed(
        self,
        user: User,
        allowed_ids: Collection[int],
    ) -> User:
        if user.telegram_id in allowed_ids:
            user.role = UserRole.SUPER_ADMIN
            user.is_active = True
            await self.session.flush()
        return user
