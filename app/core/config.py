from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    redis_url: str = "redis://localhost:6379/0"

    firebase_credentials_path: str = "./repz-5e06b-firebase-adminsdk-fbsvc-a84a929fb9.json"

    exercises_json_path: str = "./exercises.json"

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173"
    )

    media_root: str = "./media"
    public_base_url: str = "http://localhost:8000"

    admin_api_key: str = "change-me-admin-key"
    sentry_dsn: str = ""
    rate_limit_enabled: bool = True

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

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
