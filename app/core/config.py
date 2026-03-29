from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: SecretStr = Field(validation_alias="BOT_TOKEN")
    db_url: str = Field(validation_alias="DB_URL")
    super_admin_telegram_ids: tuple[int, ...] = Field(
        default_factory=tuple,
        validation_alias="SUPER_ADMIN_TELEGRAM_IDS",
    )
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    @field_validator("super_admin_telegram_ids", mode="before")
    @classmethod
    def parse_super_admin_ids(cls, value: Any) -> tuple[int, ...]:
        if value in (None, "", [], (), set()):
            return tuple()

        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            return tuple(int(item) for item in items)

        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)

        raise TypeError(
            "SUPER_ADMIN_TELEGRAM_IDS must be a comma-separated string or a sequence of integers."
        )

    @property
    def super_admin_id_set(self) -> set[int]:
        return set(self.super_admin_telegram_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()
