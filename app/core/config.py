from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Repz"
    environment: str = "development"
    debug: bool = True

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "repz"
    mysql_password: str = "repz"
    mysql_database: str = "repz"

    redis_url: str = "redis://localhost:6379/0"

    firebase_credentials_path: str = "./repz-5e06b-firebase-adminsdk-fbsvc-a84a929fb9.json"

    workoutx_api_key: str = ""
    workoutx_base_url: str = "https://api.workoutxapp.com"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    media_root: str = "./media"
    public_base_url: str = "http://localhost:8000"

    admin_api_key: str = "change-me-admin-key"
    sentry_dsn: str = ""
    rate_limit_enabled: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
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
