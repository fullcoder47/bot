from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.system_setting import SystemSetting


class SystemSettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> SystemSetting | None:
        statement = select(SystemSetting).where(SystemSetting.key == key)
        return await self.session.scalar(statement)

    async def upsert(self, key: str, value: str | None) -> SystemSetting:
        setting = await self.get(key)
        if setting is None:
            setting = SystemSetting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        await self.session.flush()
        return setting
