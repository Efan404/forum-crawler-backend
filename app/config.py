from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str
    sync_database_url: str
    redis_url: str
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    @field_validator("celery_broker_url", "celery_result_backend", mode="before")
    @classmethod
    def default_to_redis(cls, value: Optional[str], info):
        if value:
            return value
        values = info.data
        return values.get("redis_url")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

