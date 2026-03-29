from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repo import UserRepository
from app.domain.dto.user_dto import CreateUserDTO, TelegramUserDTO, UserDTO
from app.domain.enums.language import LanguageCode
from app.domain.enums.role import UserRole


class LocalizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_user_language(self, telegram_id: int) -> LanguageCode | None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user.language if user else None

    async def save_language_selection(
        self,
        telegram_user: TelegramUserDTO,
        language: LanguageCode,
    ) -> UserDTO:
        user = await self.user_repo.get_by_telegram_id(telegram_user.telegram_id)

        if user is None:
            user = await self.user_repo.create(
                CreateUserDTO(
                    telegram_id=telegram_user.telegram_id,
                    full_name=telegram_user.full_name,
                    username=telegram_user.username,
                    phone=telegram_user.phone,
                    role=UserRole.EMPLOYEE,
                    language=language,
                    is_active=False,
                )
            )
        else:
            await self.user_repo.update_profile_fields(user, telegram_user)
            await self.user_repo.update_language(user, language)

        await self.session.commit()
        return UserDTO.from_model(user)
