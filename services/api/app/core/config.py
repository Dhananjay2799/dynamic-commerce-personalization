from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dynamic Commerce Personalization API"
    environment: str = "development"

    database_url: str = (
        "postgresql+asyncpg://personalization:"
        "personalization_dev@localhost:5432/personalization"
    )

    redis_url: str = "redis://localhost:6379/0"

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()