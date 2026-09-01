from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "Dynamic Commerce Personalization API"
    environment: str = "development"

    database_url: str = (
        "postgresql+asyncpg://personalization:"
        "personalization_dev@localhost:5432/personalization"
    )

    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:3000"

    model_artifacts_dir: Path = PROJECT_ROOT / "ml" / "artifacts"
    session_ttl_seconds: int = 86400
    session_max_events: int = 50

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()