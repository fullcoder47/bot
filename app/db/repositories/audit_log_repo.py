from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        actor_telegram_id: int | None,
        action: str,
        entity_type: str,
        entity_id: int | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_telegram_id=actor_telegram_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_json,
        )
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log
