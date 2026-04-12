from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log_repo import AuditLogRepository
from app.db.repositories.system_setting_repo import SystemSettingRepository
from app.domain.enums.system_setting_key import SystemSettingKey


class SystemSettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.system_setting_repo = SystemSettingRepository(session)
        self.audit_log_repo = AuditLogRepository(session)

    @staticmethod
    def normalize_optional_value(value: str) -> str | None:
        normalized = " ".join(value.split()).strip()
        if not normalized or normalized == "-":
            return None
        return normalized

    async def get_payment_card_number(self) -> str | None:
        setting = await self.system_setting_repo.get(SystemSettingKey.PAYMENT_CARD_NUMBER.value)
        return setting.value if setting is not None else None

    async def update_payment_card_number(
        self,
        raw_value: str,
        *,
        actor_telegram_id: int | None = None,
    ) -> str | None:
        normalized_value = self.normalize_optional_value(raw_value)
        previous_value = await self.get_payment_card_number()
        await self.system_setting_repo.upsert(
            SystemSettingKey.PAYMENT_CARD_NUMBER.value,
            normalized_value,
        )
        await self.audit_log_repo.create(
            actor_telegram_id=actor_telegram_id,
            action="payment_card_updated",
            entity_type="system_setting",
            entity_id=None,
            metadata_json={
                "key": SystemSettingKey.PAYMENT_CARD_NUMBER.value,
                "previous_value": previous_value,
                "new_value": normalized_value,
            },
        )
        await self.session.commit()
        return normalized_value
