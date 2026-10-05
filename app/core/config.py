import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_url import migration_sync_url, normalize_async_url

_LOCAL_PUBLIC_BASES = {"http://localhost:8000", "http://127.0.0.1:8000"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Repz"
    environment: str = "development"
    debug: bool = True

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "repz"
    postgres_password: str = "repz"
    postgres_database: str = "repz"
    database_url: str = ""
    # Optional. When empty, Alembic derives the direct (non-pooler) host from DATABASE_URL.
    direct_database_url: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 5

    redis_url: str = "redis://localhost:6379/0"

    firebase_credentials_path: str = "./repz-5e06b-firebase-adminsdk-fbsvc-a84a929fb9.json"
    # Raw JSON, or base64 of that JSON. Used when the key file is not on the host.
    firebase_credentials_json: str = ""

    exercises_json_path: str = "./exercises.json"

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173"
    )
    # Optional regex matched in addition to cors_origins. Example: https://.*\\.vercel\\.app
    cors_origin_regex: str = ""

    media_root: str = "./media"
    public_base_url: str = "http://localhost:8000"

    admin_api_key: str = "change-me-admin-key"
    sentry_dsn: str = ""
    rate_limit_enabled: bool = True

    @model_validator(mode="after")
    def apply_platform_defaults(self) -> "Settings":
        external = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
        if external and self.public_base_url.rstrip("/") in _LOCAL_PUBLIC_BASES:
            self.public_base_url = external
        return self

    @property
    def _local_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.strip():
            url, _args = normalize_async_url(self.database_url)
            return url
        return self._local_database_url

    @property
    def asyncpg_connect_args(self) -> dict:
        if not self.database_url.strip():
            return {}
        _url, args = normalize_async_url(self.database_url)
        return args

    @property
    def alembic_database_url(self) -> str:
        raw = self.direct_database_url.strip() or self.database_url.strip()
        if raw:
            return migration_sync_url(raw)
        return self._local_database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
