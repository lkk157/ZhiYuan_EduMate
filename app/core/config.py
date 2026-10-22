"""Application configuration loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed settings singleton.

    Values are read from the project-root ``.env`` first, then process
    environment variables (environment wins).
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "EduMate"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    secret_key: str = "dev-only-change-me-please-change-me"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3307
    mysql_user: str = "edumate"
    mysql_password: str = "edumate_dev_password"
    mysql_database: str = "edumate"
    database_url: str = ""

    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_enabled: bool = True

    rag_base_url: str = "http://127.0.0.1:8000"
    rag_api_key: str = ""
    rag_timeout_seconds: int = 300
    rag_connect_timeout_seconds: int = 10
    rag_max_retries: int = 1
    rag_health_timeout_seconds: int = 3

    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 200
    seed_demo_password: str = "EduMate@2026"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        if self.app_env.lower() == "production":
            if len(self.secret_key) < 32 or "change-me" in self.secret_key:
                raise ValueError(
                    "SECRET_KEY must be a random string of at least 32 characters in production"
                )
        return self

    @property
    def database_url_async(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+asyncmy://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def database_url_sync(self) -> str:
        """Synchronous URL used by Alembic."""
        if self.database_url:
            return self.database_url.replace("+asyncmy", "+pymysql").replace("+aiosqlite", "")
        return (
            f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
