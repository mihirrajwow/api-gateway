from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "API Gateway"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production-32-chars-min"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/api_gateway"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # JWT
    jwt_secret_key: str = "change-me-in-production-32-chars-min"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    default_rate_limit: int = 100          # requests
    default_rate_limit_window: int = 60    # seconds

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/api_gateway.log"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
